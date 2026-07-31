Mode 別 system prompt と RAG answer 用 template を管理する。

- `prompts/system_fast.md`
- `prompts/system_work.md`
- `prompts/system_code.md`
- `prompts/rag_answer.md`
- `prompts/rag_user.md`

Gateway chat では mode に応じて system prompt を補完し、RAG answer では template から message を構築する。
