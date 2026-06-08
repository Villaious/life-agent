from app.core.agent import BaseAgent


class SimpleAgent(BaseAgent):
    async def run(self, user_input: str, **kwargs: object) -> str:
        response = await self.call_llm(user_input)
        self.history.add("user", user_input)
        self.history.add("assistant", response)
        return response
