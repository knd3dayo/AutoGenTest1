import os, sys, asyncio
from typing import Any
from dotenv import load_dotenv
# autogen
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import BaseChatMessage
from traceloop.sdk.decorators import workflow # type: ignore

from selector_group_chat_test_00 import create_model_client, create_termination_condition, init_trace, create_agent
from selector_group_chat_test_00 import worker_agents


@workflow(name=__file__)
async def main(input_message: str):
    # モデルクライアントを作成
    model_client = create_model_client()

    # plannerエージェント worker_agentsの情報をsystem_messageに追加
    agents_description = "\n".join([f"{agent.name}: {agent.description}" for agent in worker_agents])
    planner = create_agent(
        name="planner",
        description="ユーザーの要求を達成するための計画を考えて、各エージェントと協力して要求を達成しますト",
        system_message=""""
        ユーザーの要求を達成するための計画を考えて、各エージェントと協力して要求を達成します
        - エージェントが以下の役割を担当します。  
        {agents_description}
        - ユーザーの要求を達成するための計画を作成してタスク一覧を作成します。
        - タスクの割り当てに問題ないか？もっと効率的な計画およびタスク割り当てがないか？については対象エージェントに確認します。
        - 計画に基づき、対象のエージェントにタスクを割り当てます。
        - 計画作成が完了したら[計画作成完了]と返信してください
        その後、計画に基づきタスクを実行します。全てのタスクが完了したら、[TERMINATE]と返信してください。
        """,
        model_client=model_client,
    )

    agents = worker_agents + [planner]
    
    # plannerとagent_callerによるグループチャットを作成
    selector_prompt: str = """
    以下の会話は、ユーザーからの指示に基づいてplannerが計画したタスクを遂行するチームのチャットです。
    チームのメンバー名とその役割は次の通りです。{roles} 

    以下の会話を読んでください。タスクの遂行状況を確認して、次のタスクを遂行するために適切なメンバーを{participants}から選んでください。
    メンバー名のみを返答してください。

        {history}

    """ 
    
    chat = SelectorGroupChat(
            agents,
            model_client=model_client,
            termination_condition=create_termination_condition("[TERMINATE]", 10, 120),
            selector_prompt=selector_prompt
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