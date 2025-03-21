import os, sys, asyncio, json
from typing import Any, Sequence, Union
# openai
from openai import OpenAI
# autogen
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult, ChatAgent
from autogen_agentchat.messages import BaseChatMessage, ChatMessage, AgentEvent
from traceloop.sdk.decorators import workflow # type: ignore

from selector_group_chat_test_00 import create_model_client, create_termination_condition, init_trace, init_env
from selector_group_chat_test_00 import worker_agents, planner


def select_worker_agent(agents: list[ChatAgent], messages: Sequence[AgentEvent | ChatMessage]) -> Union[str, None]:
    """
    Select the worker agent to respond to the user message.
    """
    roles = "\n".join([agent.name + ":" + agent.description for agent in agents])
    participants = ", ".join([agent.name for agent in agents])
    history = "\n".join([f"{message.source}: {message.content}" for message in messages])
    json_format_sample = {"member": "メンバー名"}
    prompt = f"""
    以下の会話は、ユーザーからの指示に基づいてplannerが計画したタスクを遂行するチームのチャットです。
    チームのメンバー名とその役割は次の通りです。{roles} 

    以下の会話を読んでください。タスクの遂行状況を確認して、次のタスクを遂行するために適切なメンバーを{participants}から選んでください。
    出力形式はJSONで、{json_format_sample}としてください。

        {history}
    """
    init_env()
    openai_client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )

    content: Union[str, None] = response.choices[0].message.content
    if content is None:
        return None

    return json.loads(content).get("member", None)

@workflow(name=__file__)
async def main(input_message: str):
    # モデルクライアントを作成
    model_client = create_model_client()
    agents = worker_agents + [planner]
    
    # selector_funcでエージェント選択処理をカスタマイズ

    def selector_func(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
        # 最後のメッセージがplannerからのものでない場合、plannerを選択
        if messages[-1].source != planner.name:
            return planner.name
        else:
            selected_agent_name = select_worker_agent(agents, messages)
            # エージェントが選択されなかった場合、plannerを選択
            if selected_agent_name is None:
                return planner.name

            return selected_agent_name

    # SelectorGroupChatを作成。selector_funcを設定する。
    chat = SelectorGroupChat(
            agents,
            model_client=model_client,
            termination_condition=create_termination_condition("[TERMINATE]", 10, 120),
            selector_func=selector_func
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
