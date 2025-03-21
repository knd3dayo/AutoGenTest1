import os, sys, asyncio
from typing import Annotated
# autogen
from autogen_core.tools import FunctionTool
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import BaseChatMessage
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult, ChatAgent
from autogen_agentchat.messages import BaseChatMessage
from traceloop.sdk.decorators import workflow # type: ignore

from selector_group_chat_test_00 import create_model_client, create_termination_condition, create_agent, init_trace, init_env
from selector_group_chat_test_00 import worker_agents, planner

# エージェント一覧を取得する関数
def list_agents() -> Annotated[list[dict[str, str]], "List of registered agents, each containing 'name' and 'description'"]:
    """
    This function retrieves a list of registered agents.
    """
    agent_descption_list = []
    for agent in worker_agents:
        agent_descption_list.append({"name": agent.name, "description": agent.description})
    return agent_descption_list

# execute_agent
# エージェントを実行する関数
async def execute_agent(
        agent_name: Annotated[str, "Agent name"], initial_message: Annotated[str, "Input text"],
        ) -> Annotated[str, "Output text"]:
    """
    This function executes the specified agent with the input text and returns the output text.
    First argument: agent name, second argument: input text.
    - Agent name: Specify the name of the agent as the Python function name.
    - Input text: The text data to be processed by the agent.
    """
    # agent_nameに対応するエージェントを取得
    agent_list = [item for item in worker_agents if item.name == agent_name]
    agent = agent_list[0] if len(agent_list) > 0 else None

    if agent is None:
        return "The specified agent does not exist."

    output_text = ""
    # run_agent関数を使用して、エージェントを実行
    async for message in agent.run_stream(task=initial_message):
        if isinstance(message, BaseChatMessage):
            message_str = f"{message.source}(in agent selector): {message.content}"
            # print(message_str)
            output_text += message_str + "\n"

    return output_text

@workflow(name=__file__)
async def main(input_message: str):
    # モデルクライアントを作成
    model_client = create_model_client()
    
    # エージェント選択エージェントを作成
    agent_selector = create_agent(
        name="agent_selector",
        description="他のエージェントを呼び出すエージェント",
        system_message=""""
        list_agentsで呼び出し可能なエージェント一覧を取得します。そして、
        ユーザーの要求にマッチする適切なエージェントを呼び出すことができます。
        """,
        model_client=model_client,
        tools=[
            FunctionTool(execute_agent, execute_agent.__doc__, name = "execute_agent"), # type: ignore
            FunctionTool(list_agents, list_agents.__doc__ ,name = "list_agents") # type: ignore
        ] 
    )
    # 作業用エージェントリストにagent_selectorも含める場合
    # worker_agents.append(agent_selector)

    # plannerとagent_selectorによるグループチャットを作成
    chat = SelectorGroupChat(
            [planner, agent_selector],
            model_client=model_client,
            termination_condition=create_termination_condition("[TERMINATE]", 10, 120)
            )

    # グループチャットを実行
    stream = chat.run_stream(task=input_message)
    # await Console(stream)
    async for message in stream:
        if type(message) == TaskResult:
            # TaskResultの場合はチャット終了
            break
        if isinstance(message, BaseChatMessage):
            # メッセージが返された場合、エージェント名とメッセージを表示
            message_str = f"{message.source}: {message.content}"
            print(message_str)

if __name__ == '__main__':
    input_message: str = """
    宇宙について、以下の観点で情報をまとめてください
    * 宇宙の成り立ち
    * 哲学的な視点からの宇宙
    * 宇宙に関するアニメ
    """
    # traceloopによるトレース処理初期化
    init_trace()
    # メイン処理を実行
    asyncio.run(main(input_message))