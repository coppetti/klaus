"""
Exemplo 2: Router Pattern
=========================

Demonstra como criar um sistema multi-agent com routing inteligente.
"""

from agent_builder.orchestration import RouterPattern

# Definir especialistas
specialists = [
    {
        "name": "vendas_agent",
        "description": "Especialista em vendas e negociações",
        "instruction": "Você é um especialista em vendas. Ajude com orçamentos, propostas e negociações."
    },
    {
        "name": "suporte_agent",
        "description": "Especialista em suporte técnico",
        "instruction": "Você é um especialista em suporte. Resolva problemas técnicos e dúvidas."
    },
    {
        "name": "financeiro_agent",
        "description": "Especialista em finanças",
        "instruction": "Você é um especialista financeiro. Ajude com faturas, pagamentos e relatórios."
    }
]

# Criar router
router = RouterPattern.create(
    name="atendimento_router",
    model="gemini-2.0-flash-exp",
    sub_agents=specialists,
)

if __name__ == "__main__":
    print(f"Router criado: {router.name}")
    print(f"Sub-agentes: {[a.name for a in router.sub_agents]}")
    print("\nPara testar via CLI:")
    print("  eab create agent atendimento_router --type router --sub-agents 'vendas,suporte,financeiro'")
