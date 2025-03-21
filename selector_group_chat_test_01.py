import os, sys, asyncio
from typing import Any
# autogen
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import BaseChatMessage
from traceloop.sdk.decorators import workflow # type: ignore
from selector_group_chat_test_00 import create_model_client, create_termination_condition, init_trace, init_env
from selector_group_chat_test_00 import worker_agents, planner

@workflow(name=__file__)
async def main(input_message: str):
 
    # plannerとagent_callerによるグループチャットを作成
    model_client = create_model_client()
    agents = worker_agents + [planner]

    chat = SelectorGroupChat(
            agents,
            model_client=model_client,
            termination_condition=create_termination_condition("[TERMINATE]", 10, 120),
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
