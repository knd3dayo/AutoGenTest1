import os, sys
from typing import Any
from dotenv import load_dotenv
# autogen
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.tools import FunctionTool
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination, TimeoutTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult, ChatAgent
from autogen_agentchat.messages import BaseChatMessage
from traceloop.sdk import Traceloop # type: ignore

def init_env():
    # .envファイルから環境変数を読み込む
    dotenv_path = os.environ.get("DOTENV_PATH", None)
    if dotenv_path is None:
        load_dotenv()
    else:
        load_dotenv(dotenv_path)

    key = os.getenv("OPENAI_API_KEY")
    if key is None:
        raise ValueError("環境変数：OPENAI_API_KEYが設定されていません")

    key = os.getenv("TRACELOOP_API_KEY")
    if key is None:
        print("環境変数：TRACELOOP_API_KEYが設定されていません", file=sys.stderr)

def init_trace():
    init_env()
    api_key = os.getenv("TRACELOOP_API_KEY")
    if api_key is None:
        # traceloopのAPIキーが設定されていない場合は、トレースを無効にする
        return

    Traceloop.init(
        disable_batch=True,
        api_key=api_key
        )
    
# 指定したnameのLLMConfigをDBから取得して、llm_configを返す    
def create_model_client() -> OpenAIChatCompletionClient:
    init_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise ValueError("環境変数：OPENAI_API_KEYが設定されていません")

    # print(f"autogen llm_config parameters:{parameters}")
    client = OpenAIChatCompletionClient(
        api_key=api_key,
        model="gpt-4o-mini",
    )
    return client

# 指定したnameのAgentをDBから取得して、Agentを返す
def create_agent(
        name: str, description: str, system_message:str, 
        model_client: OpenAIChatCompletionClient, tools: list[FunctionTool] = [], handoffs=[] ) -> AssistantAgent:
    # AssistantAgentの引数用の辞書を作成
    params: dict[str, Any] = {}
    params["name"] = name
    params["description"] = description

    # code_executionがFalseの場合は、AssistantAgentを作成
    params["system_message"] = system_message
    # llm_config_nameが指定されている場合は、llm_config_dictを作成
    params["model_client"] = model_client
    if len(tools) > 0:
        params["tools"] = tools
    if len(handoffs) > 0:
        params["handoffs"] = handoffs

    return AssistantAgent(**params)

def create_termination_condition(termination_msg: str, max_msg: int, timeout: int):
    # 終了条件を設定
    # 最大メッセージ数、特定のテキストメッセージ、タイムアウトのいずれかが満たされた場合に終了
    max_msg_termination = MaxMessageTermination(max_messages=max_msg)
    text_termination = TextMentionTermination(termination_msg)
    time_terminarion = TimeoutTermination(timeout)
    combined_termination = max_msg_termination | text_termination | time_terminarion
    return combined_termination

# モデルクライアントを作成
model_client = create_model_client()

# テスト用エージェントを作成
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
)

# 作業用エージェントリスト
worker_agents: list[ChatAgent] =  [science_researcher, philosophy_researcher, anime_researcher]

async def main(input_message: str):
    # plannerとworker_agentsによるSelectorGroupChatを作成
    chat = SelectorGroupChat(
            [science_researcher, philosophy_researcher, anime_researcher, planner],
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

