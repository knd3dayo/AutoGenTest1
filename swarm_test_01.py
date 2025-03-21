import os, sys, asyncio
from typing import Annotated

from traceloop.sdk.decorators import workflow # type: ignore

# autogen
from autogen_core.tools import FunctionTool
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult, ChatAgent
from autogen_agentchat.messages import BaseChatMessage

from selector_group_chat_test_00 import create_model_client, create_agent, create_termination_condition, init_trace


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


# モデルクライアントを作成
model_client = create_model_client()

# plannerエージェント
planner = create_agent(
    name="planner",
    description="ユーザーの要求を達成するための計画を考えて、各エージェントと協力して要求を達成しますト",
    system_message=""""
    ユーザーの要求を達成するための計画を考えて、各エージェントと協力して要求を達成します
    - ユーザーの要求を達成するための計画を作成してタスク一覧を作成します。
    - タスクの割り当てに問題ないか？もっと効率的な計画およびタスク割り当てがないか？については対象エージェントに確認します。
    - 計画に基づき、対象のエージェントにタスクを割り当てます。
    - 計画作成が完了したら[計画作成完了]と返信してください
    その後、計画に基づきタスクを実行します。全てのタスクが完了したら、[TERMINATE]と返信してください。
    """,
    model_client=model_client,
    handoffs=["agent_selector"]
)
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
    ],
    handoffs=["planner"]
)

# 作業用エージェントを作成
science_researcher = create_agent(
    name="science_researcher",
    description="科学知識に関する質問に答えるエージェント",
    system_message="あなたは科学研究者です。科学に関する質問に答えることができます。",
    model_client=model_client,
)
philosophy_researcher = create_agent(
    name="philosophy_researcher",
    description="哲学に関する質問に答えるエージェント",
    system_message="あなたは哲学研究者です。哲学に関する質問に答えることができます。",
    model_client=model_client,
)
anime_researcher = create_agent(
    name="anime_researcher",
    description="アニメに関する質問に答えるエージェント",
    system_message="あなたはアニメ研究者です。アニメに関する質問に答えることができます。",
    model_client=model_client,
)


worker_agents: list[ChatAgent] =  [science_researcher, philosophy_researcher, anime_researcher]


@workflow(name=__file__)
async def main(input_message: str):
    # plannerとagent_selectorによるSwarmを作成
    chat = Swarm(
        participants=[planner, agent_selector], 
        termination_condition=create_termination_condition("TERMINATE", 100, 300)
    )

    # グループチャットを実行
    stream = chat.run_stream(task=input_message)
    # await Console(stream)
    async for message in stream:
        if type(message) == TaskResult:
            break
        if isinstance(message, BaseChatMessage):
            message_str = f"{message.source}: {message.content}"
            print(message_str)

if __name__ == '__main__':
    input_message: str = """
    宇宙について、以下の観点で情報をまとめてください
    * 宇宙の成り立ち
    * 哲学的な視点からの宇宙
    * 宇宙に関するアニメ
    """
    init_trace()

    asyncio.run(main(input_message))
    