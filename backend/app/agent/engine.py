import json
import re
import logging
import httpx
from typing import AsyncGenerator, Dict, Any, List
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.agent.tools import ALL_TOOLS, TOOLS_METADATA

logger = logging.getLogger(__name__)

# Core ReAct Prompt
SYSTEM_PROMPT = """You are an expert Financial Analyst & Market Research AI Agent. You specialize in conducting rigorous investment research and stock analysis.
You have access to the following tools:

{tools_descriptions}

To analyze and answer the user's inquiry, you must follow the ReAct (Reasoning and Action) loop. You will think, take actions using tools, observe their results, and iterate until you have a complete, professional answer.

For each step of the loop, you MUST write in this EXACT format:

Thought: [Explain your reasoning, what you need to find out, and which tool to use]
Action: [The exact name of the tool, must be one of: VectorSearch, StockData, WebSearch]
Parameters: [A valid JSON block of arguments for the tool matching its parameters, e.g. {{"ticker": "NVDA", "period": "3mo"}}]

Once you have gathered all necessary information and are ready to compile your final response, write in this format:

Thought: [Explain that you have enough information to build the final investment brief]
Final Answer: [Your comprehensive, highly analytical, and beautifully formatted markdown report here. Include financial ratios, trend analysis, summaries of retrieved records, and clear investment thesis if appropriate.]

RULES:
1. ONLY output ONE (Thought + Action + Parameters) block or ONE (Thought + Final Answer) block per turn. Do not write multiple actions.
2. Wait for the Observation from the system after calling a tool. Never write your own 'Observation:'.
3. If a tool call fails or returns an error, explain what happened in your next Thought and try to correct the query or use a different tool.
4. Speak the language of the user. If the user asks in Vietnamese, write your Thoughts, Final Answer, and summaries in Vietnamese. Keep tool names and parameters in English.
5. If the question can be answered directly without tools, you can skip straight to Final Answer.
"""

def format_tools_descriptions() -> str:
    descriptions = []
    for tool in TOOLS_METADATA:
        desc = (
            f"- Name: {tool['name']}\n"
            f"  Description: {tool['description']}\n"
            f"  Parameters Schema: {json.dumps(tool['parameters'])}"
        )
        descriptions.append(desc)
    return "\n\n".join(descriptions)

def parse_agent_response(text: str) -> Dict[str, Any]:
    """
    Parses the LLM's ReAct step response.
    Returns:
    {
        "thought": str,
        "action": str or None,
        "parameters": dict or None,
        "final_answer": str or None
    }
    """
    text = text.strip()
    result = {
        "thought": "",
        "action": None,
        "parameters": None,
        "final_answer": None
    }
    
    # 1. Extract Thought
    thought_match = re.search(r"Thought:\s*(.*?)(?=\n(?:Action|Final Answer):|$)", text, re.DOTALL)
    if thought_match:
        result["thought"] = thought_match.group(1).strip()
    
    # 2. Extract Final Answer (terminal condition)
    final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
    if final_match:
        result["final_answer"] = final_match.group(1).strip()
        return result
        
    # 3. Extract Action
    action_match = re.search(r"Action:\s*([a-zA-Z0-9_-]+)", text)
    if action_match:
        result["action"] = action_match.group(1).strip()
        
    # 4. Extract Parameters
    params_match = re.search(r"Parameters:\s*(\{.*\})", text, re.DOTALL)
    if params_match:
        try:
            # Clean JSON codeblock wrappers if any
            clean_json = params_match.group(1).strip()
            # If wrapped in markdown blocks
            clean_json = re.sub(r"^```json\s*", "", clean_json)
            clean_json = re.sub(r"\s*```$", "", clean_json)
            result["parameters"] = json.loads(clean_json)
        except Exception as e:
            logger.warning(f"Could not parse parameters as JSON: {params_match.group(1)}. Error: {e}")
            # Try a regex recovery for single values
            # e.g., Parameters: {"ticker": "AAPL"} -> we can search for values
            result["parameters"] = {"raw": params_match.group(1).strip()}
            
    # Fallback parsing in case the LLM did not structure parameters properly
    if result["action"] and not result["parameters"]:
        # Look for JSON anywhere in the text after Action
        json_fallback = re.search(r"(\{.*\})", text[text.find("Action:"):])
        if json_fallback:
            try:
                result["parameters"] = json.loads(json_fallback.group(1).strip())
            except:
                pass
                
    return result

async def call_ollama(prompt: str, system_prompt: str) -> str:
    """
    Submits prompt to local Ollama.
    Uses low temperature (0.1) for high adherence to ReAct structure.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "stop": ["Observation:", "OBSERVATION:"]
        }
    }
    
    logger.info(f"Submitting prompt to Ollama model '{OLLAMA_MODEL}'...")
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["response"]

async def run_agent_workflow(user_query: str, chat_history: List[Dict[str, str]] = None, max_steps: int = 8) -> AsyncGenerator[str, None]:
    """
    Runs the ReAct agent reasoning loop asynchronously.
    Yields JSON events detailing each step, tool execution, and final response.
    
    Event Types yielded:
    - {"type": "start", "query": "..."}
    - {"type": "step", "step": 1, "thought": "...", "action": "...", "parameters": {...}}
    - {"type": "observation", "step": 1, "action": "...", "output": "..."}
    - {"type": "chart_data", "ticker": "...", "data": [...], "fundamentals": {...}}  (If StockData is called)
    - {"type": "final_answer", "output": "..."}
    - {"type": "error", "message": "..."}
    """
    yield json.dumps({"type": "start", "query": user_query}) + "\n"
    
    # Structure system prompt
    tools_desc = format_tools_descriptions()
    sys_prompt = SYSTEM_PROMPT.format(tools_descriptions=tools_desc)
    
    # Build prompt content with history & query
    prompt_history = ""
    if chat_history:
        prompt_history += "Lịch sử trò chuyện trước đó:\n"
        for msg in chat_history[-6:]: # Keep last 3 turns
            role = "Người dùng" if msg["role"] == "user" else "Tác tử"
            prompt_history += f"{role}: {msg['content']}\n"
        prompt_history += "\n"
        
    prompt_history += f"Inquiry hiện tại của người dùng: {user_query}\n\nBắt đầu vòng lặp ReAct:\n"
    
    current_prompt = prompt_history
    
    step_num = 1
    stock_charts_sent = set() # Avoid sending duplicate chart data in one run
    
    while step_num <= max_steps:
        logger.info(f"--- Agent Loop Step {step_num} ---")
        
        try:
            # 1. Call LLM
            llm_output = await call_ollama(current_prompt, sys_prompt)
            logger.info(f"LLM Raw Output:\n{llm_output}")
            
            # 2. Parse output
            parsed = parse_agent_response(llm_output)
            thought = parsed["thought"] or "Đang tiến hành phân tích thông tin..."
            
            # Append this step's LLM generation to the prompt history
            current_prompt += f"\n{llm_output}\n"
            
            # 3. Handle terminal answer
            if parsed["final_answer"]:
                logger.info(f"Agent finished. Final Answer found.")
                yield json.dumps({
                    "type": "step",
                    "step": step_num,
                    "thought": thought,
                    "action": "Hoàn thành",
                    "parameters": None
                }) + "\n"
                yield json.dumps({
                    "type": "final_answer",
                    "output": parsed["final_answer"]
                }) + "\n"
                return
                
            # Check if an Action was requested
            action = parsed["action"]
            params = parsed["parameters"] or {}
            
            if not action:
                logger.warning("LLM did not request a tool and did not provide Final Answer. Prompting to complete.")
                # Auto-inject correction to force completion
                current_prompt += "\nSystem: You did not select an Action nor output Final Answer. If you have gathered all details, write 'Final Answer: [brief]'. Otherwise, select a valid tool.\n"
                step_num += 1
                continue
                
            # Send step event to client
            yield json.dumps({
                "type": "step",
                "step": step_num,
                "thought": thought,
                "action": action,
                "parameters": params
            }) + "\n"
            
            # 4. Execute tool
            if action not in ALL_TOOLS:
                observation = f"Error: Tool '{action}' does not exist. Choose one of: {list(ALL_TOOLS.keys())}."
                logger.error(observation)
            else:
                try:
                    tool_func = ALL_TOOLS[action]
                    
                    # Safe parameters mapping
                    if action == "VectorSearch":
                        query_arg = params.get("query", user_query)
                        tool_result = tool_func(query_arg)
                        observation = tool_result
                        
                    elif action == "StockData":
                        ticker_arg = params.get("ticker", "").strip().upper()
                        period_arg = params.get("period", "3mo")
                        
                        if not ticker_arg:
                            # Try to extract ticker from raw parameters
                            raw_val = params.get("raw", "")
                            ticker_match = re.search(r"['\"]?([a-zA-Z]{1,5})['\"]?", raw_val)
                            ticker_arg = ticker_match.group(1).upper() if ticker_match else ""
                            
                        if not ticker_arg:
                            observation = "Error: StockData tool requires a 'ticker' parameter."
                        else:
                            tool_result = tool_func(ticker_arg, period_arg)
                            
                            # If successful, yield chart data to frontend so it displays alongside the chat!
                            if tool_result.get("status") == "success" and ticker_arg not in stock_charts_sent:
                                yield json.dumps({
                                    "type": "chart_data",
                                    "ticker": ticker_arg,
                                    "fundamentals": tool_result["fundamentals"],
                                    "chart_data": tool_result["chart_data"]
                                }) + "\n"
                                stock_charts_sent.add(ticker_arg)
                                
                            observation = tool_result["llm_summary"]
                            
                    elif action == "WebSearch":
                        query_arg = params.get("query", user_query)
                        tool_result = tool_func(query_arg)
                        observation = tool_result
                        
                    else:
                        observation = "Error: Invalid tool selected."
                except Exception as ex:
                    logger.error(f"Exception executing tool {action}: {ex}")
                    observation = f"Exception executing tool {action}: {str(ex)}"
                    
            logger.info(f"Tool {action} Observation: {observation[:200]}...")
            
            # Send observation event to client
            yield json.dumps({
                "type": "observation",
                "step": step_num,
                "action": action,
                "output": observation
            }) + "\n"
            
            # Feed the observation back into the current prompt
            current_prompt += f"Observation: {observation}\n"
            
        except Exception as e:
            logger.error(f"Error in agent step {step_num}: {e}")
            yield json.dumps({
                "type": "error",
                "message": f"Error occurred during agent reasoning: {str(e)}"
            }) + "\n"
            return
            
        step_num += 1
        
    # Exceeded maximum steps
    logger.warning("Agent reached maximum step limit.")
    yield json.dumps({
        "type": "error",
        "message": "Vượt quá số bước suy luận tối đa (max steps limit). Agent dừng hoạt động để tránh vòng lặp vô hạn."
    }) + "\n"
