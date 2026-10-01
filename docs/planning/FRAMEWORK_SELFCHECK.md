# COAGENTS 框架詳細規格：跨文件自檢

作者／責任歸屬：滴。2026-10-01。
對象完整路徑：/home/sky/projects/agent-project-control/docs/planning/。
狀態：規劃候選的自檢，不是獨立AUDIT、不授權DEV、不聲稱產品驗收PASS。

## 1. 實際檢查射程

| 格 | 正向結果 | 必紅突變 | 不能證什麼 |
|---|---|---|---|
| 操作ID及Method+path唯一 | 設計表無重複 | 追加相同item_claim；另名同路由 | 產品router真的掛上 |
| Request具名schema | 每個write/input都有詞典入口 | 拿掉WriteSetCreate | Pydantic/OpenAPI可編譯、欄位驗證已生效 |
| Action雙向對帳 | API actions均有matrix規則；matrix僅四個ops-only action不開API | 拿掉item.write_set.manage規則 | Runtime權限/角色/物件隔離正確 |
| SQL table對帳 | API引用table均有模型條目 | 拿掉gate_waivers | 可執行DDL、FK/鎖/rollback正確 |
| 文件引用 | 本詳細規格五檔的local links都存在 | 缺檔由exists檢查報出 | 連結本文語意正確／外部網址可用 |

陰性對照在記憶體修改字串，原規格不動；逐格actual_failure_fields保存在JSON。
兩份設計都是同一作者，這只是cross-file consistency，不能冒稱獨立資料來源或獨立驗收。
表內Request與SQL詞彙完整，不等於所有欄位已編成機器schema；那是DEV交付。

## 2. 語意對帳與本輪修正

- 新專案先建immutable proposal，授權綁server配給的project UUID；批准後不可換team/controller/本文。
- 同案與同workspace的複合FK、revision所屬resource、policy compiled binding、Gate waiver具名落表。
- 同repo跨案write-set以canonical source identity排他，不能用兩個repo UUID或功能label避同檔碰撞。
- UNKNOWN_EFFECT用追加reconciliation receipt；不改原票、不盲重送、不以SQL rollback假裝追回網路效果。
- read inbox不標READ；status/progress/quality/runtime分開；0必要Gate不通過、同identity換actor不獨立。
- Rule是內容權威，compiled policy是exact revision投影；自由文字和Template不能給權。
- 成功需要commit receipt／readback；async只回operation pending，不能文字宣稱已送達／完工。

以上是設計修正；未執行runtime負控。
安全skill使本版採用逐物件/欄位ACL、閉schema、cookie CSRF、secret不輸出及受限出站；
工具自檢skill使API/MCP/Dashboard共用同一action lock／validator／transaction／receipt。
TACLAW專用NL04/leaf/ToolRegistryV2不適用，本輪不改TACLAW。

## 3. 可重播量法

從repo根目錄執行以下只讀Python，stdout為結果；真LLM／供應商HTTP／外部DB寫入0。

```bash
python3 - <<'PY'
from pathlib import Path
import re,json,hashlib,collections,datetime
root=Path.cwd(); base=root/'docs/planning'
names=['FRAMEWORK_SPEC.md','API_CONTRACT.md','SQL_MODEL.md','AUTHORIZATION_MATRIX.md','STATE_MACHINES.md']
texts={n:(base/n).read_text() for n in names}
def parse(api,auth,sql):
 rows=[]
 for line in api.splitlines():
  if re.match(r'^\| [a-z][a-z0-9_]* \| (GET|POST|PATCH|PUT|DELETE) ',line):
   a=[v.strip() for v in line.split('|')[1:-1]]
   rows.append(dict(operation_id=a[0],method=a[1].split(' ',1)[0],path=a[1].split(' ',1)[1],request=a[2],result=a[3],actions=[(v if '.' in v else a[4].split('/')[0].rsplit('.',1)[0]+'.'+v) for v in a[4].split('/')],tables=[x.strip() for x in a[5].split(',')]))
 matrix=set()
 for line in auth.splitlines():
  if line.startswith('| ') and line.count('|')==7: matrix.update(re.findall(r'\b[a-z][a-z_]*(?:\.[a-z_]+)+\b',line.split('|')[1]))
 schemas=set()
 for line in api.splitlines():
  if re.match(r'^\| [A-Z][A-Za-z]+ \|',line): schemas.add(line.split('|')[1].strip())
 schemas|={'Disposition','RawProviderEvent','OIDCCallback'}
 tables=set(re.findall(r'^\| ([a-z][a-z0-9_]+) \|',sql,re.M))
 tables|={'resources','resource_revisions','grant_record_kinds','grant_write_scopes','migration_ledger','migration_attempts','backup_manifest'}
 actions={a for r in rows for a in r['actions']}
 ids=collections.Counter(r['operation_id'] for r in rows)
 paths=collections.Counter((r['method'],r['path']) for r in rows)
 errors=dict(duplicate_operation_ids=sorted(x for x,n in ids.items() if n>1),
  duplicate_method_paths=sorted('/'.join(x) for x,n in paths.items() if n>1),
  missing_request_schemas=sorted({r['request'] for r in rows if r['request']!='—'}-schemas),
  missing_action_rules=sorted(actions-matrix),
  matrix_without_api=sorted(matrix-actions-{'system.migrate','system.deploy','system.backup','system.restore'}),
  missing_sql_tables=sorted({t for r in rows for t in r['tables']}-tables))
 return rows,schemas,tables,actions,errors
api,auth,sql=(texts[n] for n in ['API_CONTRACT.md','AUTHORIZATION_MATRIX.md','SQL_MODEL.md'])
rows,schemas,tables,actions,errors=parse(api,auth,sql)
assert rows and all(not v for v in errors.values()),errors
negative=[]
for key,ma,mt,ms,expected in [
 ('REMOVE_ACTION_RULE',api,auth.replace('item.write_set.manage','omitted.write_set',1),sql,'missing_action_rules'),
 ('REMOVE_REQUEST_SCHEMA',api.replace('| WriteSetCreate |','| RemovedSchema |',1),auth,sql,'missing_request_schemas'),
 ('REMOVE_SQL_TABLE',api,auth,sql.replace('| gate_waivers |','| removed_gate_table |',1),'missing_sql_tables'),
 ('DUPLICATE_OPERATION',api+'\n'+next(l for l in api.splitlines() if l.startswith('| item_claim |')),auth,sql,'duplicate_operation_ids'),
 ('DUPLICATE_ROUTE',api+'\n'+next(l for l in api.splitlines() if l.startswith('| item_claim |')).replace('| item_claim |','| fake_claim |',1),auth,sql,'duplicate_method_paths')]:
 e=parse(ma,mt,ms)[-1]
 assert e[expected],(key,e)
 negative.append(dict(control=key,expected_failure_field=expected,actual_failures={k:v for k,v in e.items() if v},detected=True))
link_failures=[]
for n,t in texts.items():
 for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',t):
  if '://' in link or link.startswith('#'): continue
  target=(base/link.split('#')[0])
  if not target.exists(): link_failures.append(dict(source=n,target=link))
assert not link_failures,link_failures
report=dict(author='滴',kind='STATIC_DESIGN_CONSISTENCY_ONLY',measured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 root=str(root),operation_count=len(rows),action_count=len(actions),schema_vocabulary_count=len(schemas),referenced_request_schema_count=len({r['request'] for r in rows if r['request']!='—'}),defined_table_count=len(tables),
 errors=errors,negative_controls=negative,links_checked=True,link_failures=link_failures,
 files=[dict(path='docs/planning/'+n,sha256=hashlib.sha256((base/n).read_bytes()).hexdigest(),bytes=(base/n).stat().st_size) for n in names],
 not_proven=['OpenAPI compilation','PostgreSQL DDL and transactions','permission runtime','MCP and browser parity','SSO and external providers','independent review','deployment and restoration','real-team onboarding'],
 provider_requests=0,product_code_changed=False,production_access=False,dev_authorized=False)
print(json.dumps(report,ensure_ascii=False,indent=2))
PY
```

當次結果：[framework_selfcheck.json](framework_selfcheck.json)。輸入檔SHA／bytes在JSON，未關能力逐一列出。
若規格再改，出successor結果，不使用舊JSON替新內容背書。

## 4. 完成界線

本輪只關「詳細設計缺頁／具名映射缺口」；所有B/R/X產品格維持原矩陣狀態。
仍待使用者核定設計並准DEV；正式DDL/OpenAPI/SQL/登入/worker/MCP/瀏覽器/真團隊/正式部署/restore/長期運作沒有新PASS。
之前的產品工作樹草稿未接線、未commit到本次文件包、未部署；服役v0.2另用容器三檔SHA對固定基線。

