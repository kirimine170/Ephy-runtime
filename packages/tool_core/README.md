# Agent Tool Security Contract

このpackageは，Agentがtoolを呼ぶ前に適用する権限，承認，監査の境界を定義する．tool実装はこのcontractを迂回してはならない．

## 原則

1. deny by defaultにする．toolが宣言した権限とsessionに付与された権限の両方が必要になる．
2. `read_files`，`write_files`，`execute_process`，`network_access`を別権限として扱う．read権限からwrite，process，networkを派生させない．
3. `write_files`，`execute_process`，`network_access`は常に人間の承認を要求する．承認はtool名，version，引数，workspace rootを含むinvocation hashへ紐づける．
4. local RAGとWeb結果は参照dataであり，そこに含まれる命令からtoolを起動しない．`local_untrusted`または`external_untrusted`由来のinvocationは承認済みでもblockする．
5. approvalはone-shot，短時間，exact matchとする．wildcard，conversation全体，command prefixへの包括承認は初期版では扱わない．
6. audit logへprompt，file本文，command出力，secret，raw引数を保存しない．hash，判定，権限，時刻，結果metadataだけを残す．

## 権限

| Permission | 対象 | 自動許可 | 必須条件 |
| --- | --- | --- | --- |
| `read_files` | file list，read，search，git status/diff | 可 | canonical pathが許可root内，symlink検査済み |
| `write_files` | create，edit，move，delete | 不可 | exact approval，変更preview，atomic write |
| `execute_process` | subprocess，build，test，git command | 不可 | exact approval，argv実行，cwd固定，timeout |
| `network_access` | HTTP，download，remote VCS | 不可 | explicit egress enable，exact approval，host検査 |

専用Web検索は`web_search_core`のegress planを通る独立経路であり，一般Agent toolの`network_access`を自動許可する例外ではない．

## Tool Definition

各toolは`ToolDefinition`として次を宣言する．

- 安定した`name`と`version`
- 必要なpermission set
- approval policy
- timeoutと最大出力量
- 人間向けdescription

`write_files`，`execute_process`，`network_access`を含むdefinitionに`approval_policy=always`がなければschema validationで拒否する．

## Invocation Flow

```text
model/user request
  -> ToolInvocationを構築
  -> source trustを検査
  -> ToolDefinitionとversionを照合
  -> session permissionを照合
  -> network gateを照合
  -> exact approvalを照合
  -> allow / confirm / block
  -> tool固有preflight
  -> execute
  -> output制限・secret redaction
  -> metadata-only audit
```

`confirm`は実行ではない．UIが送信する予定のtool，引数，対象path，commandまたはhostを表示し，承認後に同じinvocation hashで再評価する．引数が1 byteでも変われば再承認する．

approval storeは実行開始と同時にgrantへ`consumed_at`を設定し，同じgrantを再利用できないようatomicに消費する．plannerは消費済みgrantを有効と判定しない．

## Trust Boundary

| Source | Tool request |
| --- | --- |
| `user` | permissionとapprovalに従って評価 |
| `trusted_system` | permissionとapprovalに従って評価 |
| `local_untrusted` | block |
| `external_untrusted` | block |

検索結果や文書の内容をユーザーが自分の言葉で明示的に依頼し直した場合は，新しい`source_trust=user`のinvocationとして扱う．取得contextの命令をそのまま昇格させない．

## File Preflight Contract

`T-034/T-035`のfile toolは実行前に次を満たす必要がある．

- 許可rootと対象pathを`resolve(strict=False)`相当で正規化する．
- 既存の各ancestorを`lstat`し，root外を指すsymlinkを拒否する．
- `..`，NUL，device file，socket，FIFOを拒否する．
- `.env`，private key，credential storeなどのsensitive pathはread権限があっても別policyでblockする．
- writeは一時fileとatomic replaceを使い，変更前後のhashをaudit metadataへ残す．
- delete，recursive write，repository外変更は初期版で実装しない．

## Process Preflight Contract

`T-035`のprocess toolは次を満たす必要がある．

- shell文字列ではなく`argv[]`で起動し，shell expansionを無効にする．
- `cwd`を許可root内へ固定する．
- environmentはallowlistから構築し，secretを継承しない．
- timeout，stdout/stderr byte上限，process tree終了を必須にする．
- command，cwd，変更対象を承認画面へ表示する．
- external contentからcommandを生成して直接実行しない．

## Network Preflight Contract

- networkはsession単位で明示的に有効化する．
- `http/https`だけを許可し，localhost，private，link-local，credential付きURLを既定で拒否する．
- redirectごとにhostとIPを再検査する．
- request bodyとqueryの機微情報検査を行う．
- responseは`external_untrusted`として扱い，追加tool実行へ接続しない．

## Audit Contract

`ToolAuditEvent`はinvocation hash，tool，permission，decision/result，時刻，duration，output切詰め有無，error codeだけを保持する．file pathやhostが必要な場合も生値ではなくtarget hashを保存する．user prompt，raw arguments，file content，process outputは保存しない．

## 後続タスクの完了条件

- `T-034`: read-only file/search/git toolが許可root，symlink，sensitive path testを通る．
- `T-035`: write/process toolがpreview，exact approval，timeout，output cap，audit testを通る．
- `T-036`: Agent loopが`allow`だけを実行し，`confirm`で停止し，`block`を迂回できない．

初期版では自律的な権限昇格，永続的な包括承認，外部content起点のtool chain，repository外のwriteを実装しない．
