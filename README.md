## ファイル説明

### selector_group_chat_test_00.py
SelectorGroupChatを実行するための必要な関数、エージェントなどを定義しています。
以下のエージェントを定義しています。
* ユーザーの質問から計画とタスク一覧を作成する計画エージェント(planner)
* 科学、哲学、アニメに詳しい作業用エージェント(science_researcher、philosophy_researcher、anime_researcher)

### selector_group_chat_test_01.py

* selector_group_chat_test_00.pyで定義したエージェントを使用したSelectorGroupChat
* エージェント選択はデフォルトの動作で行われます。

### selector_group_chat_test_02.py

* selector_group_chat_test_00.pyで定義したエージェントを使用したSelectorGroupChat
* selector_messageでエージェント選択動作をカスタマイズしています。

### selector_group_chat_test_03.py

* selector_group_chat_test_00.pyで定義したエージェントを使用したSelectorGroupChat
* selector_funcでエージェント選択動作をカスタマイズしています。

### selector_group_chat_test_04.py
* selector_group_chat_test_00.pyで定義したエージェントを使用したSelectorGroupChat
* list_agents, execute_agent関数を呼び出すことが可能なエージェント選択エージェント(agent_selector)によりエージェント選択を行います。

### selector_group_chat_test_05.py
* selector_group_chat_test_00.pyで定義したエージェントを使用したSelectorGroupChat
* plannerに予め作業用エージェントの情報を渡して計画、タスク作成が行えるようにしています。

### swarm_test_01.py
* selector_group_chat_test_04.pyのSwarm版


## 使用法
```
pip install -r requirements.txt
python <ファイル名>
```
