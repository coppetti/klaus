"""
Exemplo 8: Agente Complexo com Código Python
============================================

Quando você precisa de lógica customizada, tools próprias,
ou integrações específicas que não existem no YAML.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.adk.agents import LlmAgent
from google.adk.tools import tool


# ============================================================================
# TOOL CUSTOMIZADA: Consulta Sistema Interno
# ============================================================================

@tool
def consultar_crm(cliente_id: str) -> Dict[str, Any]:
    """
    Consulta dados do cliente no CRM interno.
    
    Args:
        cliente_id: ID único do cliente
        
    Returns:
        Dados do cliente: nome, segmento, histórico de compras, status
    """
    # Simulação - aqui você conectaria à sua API real
    # Exemplo: requests.get(f"https://api.crm.company.com/clientes/{cliente_id}")
    
    clientes_db = {
        "CLI001": {
            "nome": "Empresa ABC Ltda",
            "segmento": "Enterprise",
            "historico": ["Compra R$ 50k (2024-01)", "Renovação R$ 45k (2024-06)"],
            "status": "Ativo",
            "satisfacao": 4.5,
            "contato_preferido": "email"
        },
        "CLI002": {
            "nome": "Startup XYZ",
            "segmento": "SMB",
            "historico": ["Trial", "Compra R$ 5k (2024-03)"],
            "status": "Em risco",
            "satisfacao": 2.8,
            "contato_preferido": "whatsapp"
        }
    }
    
    cliente = clientes_db.get(cliente_id)
    if not cliente:
        return {"erro": f"Cliente {cliente_id} não encontrado"}
    
    return cliente


@tool
def calcular_desconto_negociado(
    valor_base: float,
    segmento: str,
    historico_compras: int,
    urgencia: str
) -> Dict[str, Any]:
    """
    Calcula desconto baseado em regras de negócio complexas.
    
    Args:
        valor_base: Valor da proposta
        segmento: Enterprise, Mid-Market, SMB
        historico_compras: Número de compras anteriores
        urgencia: baixa, media, alta
        
    Returns:
        Valor final, desconto aplicado, aprovação necessária
    """
    desconto_base = 0.0
    
    # Regra 1: Desconto por segmento
    if segmento == "Enterprise":
        desconto_base += 0.15
    elif segmento == "Mid-Market":
        desconto_base += 0.10
    else:
        desconto_base += 0.05
    
    # Regra 2: Desconto por fidelidade
    if historico_compras >= 5:
        desconto_base += 0.10
    elif historico_compras >= 3:
        desconto_base += 0.05
    
    # Regra 3: Ajuste por urgência
    if urgencia == "alta":
        desconto_base += 0.05  # Desconto extra para fechar rápido
    
    # Limite máximo de desconto
    desconto_maximo = 0.30
    desconto_final = min(desconto_base, desconto_maximo)
    
    valor_desconto = valor_base * desconto_final
    valor_final = valor_base - valor_desconto
    
    # Regra 4: Aprovação necessária
    precisa_aprovacao = desconto_final > 0.20 or valor_final > 100000
    
    return {
        "valor_original": valor_base,
        "desconto_percentual": f"{desconto_final:.1%}",
        "valor_desconto": round(valor_desconto, 2),
        "valor_final": round(valor_final, 2),
        "precisa_aprovacao": precisa_aprovacao,
        "nivel_aprovacao": "Diretor" if valor_final > 500000 else "Gerente" if precisa_aprovacao else None,
        "validade_proposta": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    }


@tool
def agendar_follow_up(
    cliente_id: str,
    tipo_contato: str,
    data_preferencia: str,
    observacoes: str
) -> Dict[str, Any]:
    """
    Agenda follow-up no sistema de vendas.
    
    Args:
        cliente_id: ID do cliente
        tipo_contato: email, telefone, reuniao, whatsapp
        data_preferencia: Data sugerida (YYYY-MM-DD)
        observacoes: Notas sobre o que tratar
        
    Returns:
        Confirmação com ID do agendamento
    """
    # Integração real: Salesforce, HubSpot, Pipedrive, etc
    
    # Validação de data
    try:
        data_obj = datetime.strptime(data_preferencia, "%Y-%m-%d")
        if data_obj < datetime.now():
            return {"erro": "Data não pode ser no passado"}
    except ValueError:
        return {"erro": "Formato de data inválido. Use YYYY-MM-DD"}
    
    # Criar agendamento (simulação)
    agendamento_id = f"AGD-{datetime.now().strftime('%Y%m%d')}-{hash(cliente_id) % 10000}"
    
    return {
        "id_agendamento": agendamento_id,
        "cliente_id": cliente_id,
        "tipo_contato": tipo_contato,
        "data": data_preferencia,
        "status": "Agendado",
        "observacoes": observacoes,
        "criado_em": datetime.now().isoformat(),
        "responsavel": "vendedor_atual"  # Buscaria do sistema
    }


# ============================================================================
# AGENTE COMPLEXO: Vendedor Enterprise
# ============================================================================

vendedor_enterprise = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="vendedor_enterprise",
    description="Vendedor especializado em contas Enterprise com acesso a CRM e pricing",
    instruction="""
    Você é um vendedor sênior especializado em contas Enterprise.
    
    CAPACIDADES ESPECIAIS:
    - Acesso ao CRM: consulte histórico completo do cliente
    - Pricing dinâmico: calcule descontos seguindo políticas da empresa
    - Agendamento: marque follow-ups automaticamente
    
    WORKFLOW DE VENDAS:
    
    1. QUALIFICAÇÃO (sempre primeiro)
       - Pergunte: tamanho da empresa, segmento, urgência
       - Consulte CRM se tiver cliente_id
       
    2. ENTENDIMENTO DE NECESSIDADES
       - Qual problema estão tentando resolver?
       - Orçamento disponível?
       - Timeline de decisão?
       
    3. PROPOSTA
       - Se tiver todos os dados, use calcular_desconto_negociado
       - Explique o valor, não apenas o preço
       - Mencione ROI e cases similares
       
    4. OBJEÇÕES
       - Caro? Compare com valor, não concorrentes
       - Complexo? Ofereça POC/piloto
       - Timing? Use agendar_follow_up
       
    5. FECHAMENTO
       - Quando houver sinal de interesse, sugira próximo passo claro
       - Se precisar de aprovação de desconto, informe prazo
    
    REGRAS DE NEGÓCIO:
    - Nunca prometa desconto sem calcular via sistema
    - Sempre valide cliente no CRM antes de fazer proposta
    - Máximo desconto sem aprovação: 20%
    - Propostas válidas por 7 dias
    
    TOM:
    - Consultivo, não pushy
    - Orientado a dados (use o CRM)
    - Confiante mas não arrogante
    """,
    tools=[
        consultar_crm,
        calcular_desconto_negociado,
        agendar_follow_up,
    ],
)

__all__ = ["vendedor_enterprise", "consultar_crm", "calcular_desconto_negociado", "agendar_follow_up"]


# ============================================================================
# TESTE LOCAL
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    
    async def test():
        session_service = InMemorySessionService()
        runner = Runner(agent=vendedor_enterprise, session_service=session_service)
        
        session = session_service.create_session(
            app_name="vendedor_enterprise",
            user_id="test"
        )
        
        # Teste: Simular conversa
        mensagens = [
            "Olá, tenho interesse em sua solução",
            "Meu cliente_id é CLI001",
            "Preciso de orçamento para 100 licenças",
            "Quanto custa?",
        ]
        
        for msg in mensagens:
            print(f"\n👤 Cliente: {msg}")
            print("🤖 Vendedor: ", end="", flush=True)
            
            events = []
            async for event in runner.run_async(
                user_id="test",
                session_id=session.id,
                new_message=msg
            ):
                events.append(event)
            
            if events:
                last = events[-1]
                if hasattr(last, 'content'):
                    print(last.content)
    
    asyncio.run(test())
