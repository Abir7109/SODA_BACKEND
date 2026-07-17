from .base_agent import BaseAgent


class DatabaseAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="agent_database",
            description="Optimize database performance, design schemas, write efficient queries, and debug slow queries. Handles PostgreSQL, MySQL, indexing strategies, schema design, query optimization, and migration planning."
        )

    @property
    def tool_definitions(self) -> list:
        return [{
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "task": {
                        "type": "STRING",
                        "description": "Database task: 'optimize' (tune slow query/schema), 'design' (create schema), 'index' (suggest indexes), 'migrate' (plan migration), or 'explain' (analyze query plan)"
                    },
                    "query": {
                        "type": "STRING",
                        "description": "The SQL query or schema DDL to analyze"
                    },
                    "db_type": {
                        "type": "STRING",
                        "description": "Database type: 'postgresql', 'mysql', 'supabase', 'planetscale'"
                    },
                    "context": {
                        "type": "STRING",
                        "description": "Table structures, schema, or performance requirements"
                    }
                },
                "required": ["task"]
            }
        }]

    async def execute(self, task: str = "", query: str = "",
                      db_type: str = "postgresql", context: str = "", **kwargs) -> dict:
        valid = ["optimize", "design", "index", "migrate", "explain"]
        if task not in valid:
            return {"success": False, "error": f"Invalid task '{task}'. Valid: {', '.join(valid)}"}

        system_prompt = (
            "You are a database performance expert who thinks in query plans, indexes, and connection pools. "
            f"You specialize in {db_type}. "
            "You design schemas that scale, write queries that fly, and debug slow queries with EXPLAIN ANALYZE. "
            "Core expertise: indexing strategies (B-tree, GiST, GIN, partial), schema design (normalization v denormalization), "
            "N+1 detection, connection pooling, migration strategies, and zero-downtime deployments.\n\n"
            "Every query must have a plan, every foreign key must have an index, "
            "every migration must be reversible, and every slow query must get optimized."
        )

        prompts = {
            "optimize": f"Optimize this {db_type} query or schema:\n\nQuery:\n{query}\n\nContext:\n{context}\n\nProvide: the slow query plan analysis, specific indexes to add, rewritten query, and expected improvement.",
            "design": f"Design a {db_type} schema for:\n\n{context}\n\nProvide: complete DDL, indexed columns, relationships, and migration plan.",
            "index": f"Suggest indexes for:\n\nQuery:\n{query}\n\nSchema:\n{context}\n\nProvide: specific CREATE INDEX statements with type (B-tree/GIN/GiST), EXPLAIN plan showing the improvement, and maintenance considerations.",
            "migrate": f"Plan a database migration for:\n\n{context}\n\nProvide: step-by-step migration with zero-downtime approach, rollback steps, and performance impact assessment.",
            "explain": f"Explain this query plan for {db_type}:\n\n{query}\n\nBreak down: scan type, join strategy, sort method, estimated vs actual rows, and what to optimize."
        }

        result = await self.call_gemini(system_prompt, prompts.get(task, query), timeout=45)
        return {
            "success": result.get("success", False),
            "task": task,
            "db_type": db_type,
            "result": result.get("content", ""),
            "error": result.get("error"),
        }
