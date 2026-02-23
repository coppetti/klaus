"""
Exemplo 9: Abordagem Híbrida - YAML + Código
============================================

Combina a facilidade do YAML com a flexibilidade do código.
YAML define a estrutura, código implementa as tools complexas.
"""

# ============================================================================
# PARTE 1: Código Python (Tools Customizadas)
# ============================================================================

import json
from datetime import datetime
from typing import Any, Dict

from google.adk.tools import tool


@tool
def analisar_sentimento_feedback(feedback_text: str) -> Dict[str, Any]:
    """
    Analisa sentimento de feedback de cliente usando lógica customizada.
    
    Na prática, isso poderia chamar uma API externa de NLP
    ou usar um modelo específico de análise de sentimento.
    """
    # Lógica simplificada para exemplo
    # Em produção: integração com API de NLP
    
    palavras_positivas = ["ótimo", "excelente", "bom", "gostei", "perfeito", "recomendo"]
    palavras_negativas = ["ruim", "péssimo", "lento", "bug", "erro", "frustrante", "odeio"]
    
    texto_lower = feedback_text.lower()
    
    score_pos = sum(1 for p in palavras_positivas if p in texto_lower)
    score_neg = sum(1 for n in palavras_negativas if n in texto_lower)
    
    if score_pos > score_neg:
        sentimento = "positivo"
        score = min(0.5 + (score_pos - score_neg) * 0.1, 1.0)
    elif score_neg > score_pos:
        sentimento = "negativo"
        score = max(0.5 - (score_neg - score_pos) * 0.1, 0.0)
    else:
        sentimento = "neutro"
        score = 0.5
    
    return {
        "sentimento": sentimento,
        "score": round(score, 2),
        "prioridade": "alta" if sentimento == "negativo" and score < 0.3 else "normal",
        "palavras_chave": [p for p in palavras_positivas + palavras_negativas if p in texto_lower],
        "analise_data": datetime.now().isoformat()
    }


@tool
def consultar_base_conhecimento(problema: str) -> Dict[str, Any]:
    """
    Consulta base de conhecimento interna para soluções.
    """
    # Base de conhecimento simulada
    kb = {
        "login": {
            "sintomas": ["não consigo logar", "senha inválida", "acesso bloqueado"],
            "solucao": "1. Limpar cache do navegador\n2. Tentar recuperação de senha\n3. Verificar se caps lock está ativado",
            "categoria": "Acesso",
            "tempo_estimado": "5 minutos"
        },
        "performance": {
            "sintomas": ["lento", "travando", "timeout", "demora"],
            "solucao": "1. Verificar conexão de internet\n2. Fechar abas não utilizadas\n3. Tentar em horário de menor pico",
            "categoria": "Performance",
            "tempo_estimado": "10 minutos"
        },
        "integracao": {
            "sintomas": ["não sincroniza", "erro api", "webhook falhou"],
            "solucao": "1. Verificar credenciais da integração\n2. Revalidar tokens\n3. Testar endpoint manualmente",
            "categoria": "Integrações",
            "tempo_estimado": "30 minutos"
        }
    }
    
    problema_lower = problema.lower()
    
    # Matching simples
    for categoria, dados in kb.items():
        for sintoma in dados["sintomas"]:
            if sintoma in problema_lower:
                return {
                    "encontrado": True,
                    "categoria": dados["categoria"],
                    "solucao": dados["solucao"],
                    "tempo_estimado": dados["tempo_estimado"],
                    "escalar_se_nao_resolver": categoria == "integracao"
                }
    
    return {
        "encontrado": False,
        "mensagem": "Não encontramos solução automática. Escalando para técnico."
    }


# Exportar tools para uso
__all__ = ["analisar_sentimento_feedback", "consultar_base_conhecimento"]


# ============================================================================
# PARTE 2: YAML de Configuração
# ============================================================================

"""
Arquivo: agents/suporte_hibrido.yaml

name: suporte_hibrido
type: llm
model: gemini-2.0-flash-exp

description: Agente de suporte com análise de sentimento e base de conhecimento

instruction: |
  Você é um especialista em suporte ao cliente.
  
  SUPERPODERES:
  - Análise de sentimento: detecte emoção no feedback
  - Base de conhecimento: consulte soluções documentadas
  
  WORKFLOW:
  1. Sempre analise o sentimento da mensagem inicial
  2. Se sentimento negativo ALTO → prioridade máxima, seja proativo
  3. Consulte base de conhecimento antes de propor solução
  4. Se encontrar solução → guie passo a passo
  5. Se não encontrar → escale com contexto completo
  
  COMUNICAÇÃO:
  - Cliente irritado? Reconheça a frustração antes de solucionar
  - Cliente satisfeito? Agradeça e peça recomendação
  - Sempre confirme se a solução resolveu antes de encerrar

tools:
  # Tools do sistema
  - google_search
  
  # Tools customizadas (importadas do código Python)
  # Nota: No código real, registramos estas tools no agente

temperature: 0.4
"""


# ============================================================================
# PARTE 3: Registro do Agente Híbrido
# ============================================================================

def criar_agente_hibrido():
    """
    Cria agente combinando config YAML + código Python.
    
    Esta função demonstra como juntar as duas abordagens.
    """
    from google.adk.agents import LlmAgent
    from google.adk.tools import google_search
    
    # Aqui você poderia carregar o YAML e adicionar as tools do código
    agent = LlmAgent(
        model="gemini-2.0-flash-exp",
        name="suporte_hibrido",
        description="Agente de suporte com análise de sentimento e KB",
        instruction="""
        Você é um especialista em suporte ao cliente.
        
        CAPACIDADES ESPECIAIS:
        - analisar_sentimento_feedback: detecte emoção no feedback
        - consultar_base_conhecimento: acesse soluções documentadas
        
        WORKFLOW:
        1. Sempre analise o sentimento da mensagem inicial
        2. Se sentimento negativo ALTO → prioridade máxima, seja proativo  
        3. Consulte base de conhecimento antes de propor solução
        4. Se encontrar solução → guie passo a passo
        5. Se não encontrar → escale com contexto completo
        """,
        tools=[
            google_search,
            analisar_sentimento_feedback,  # Do código Python
            consultar_base_conhecimento,   # Do código Python
        ],
    )
    
    return agent


# Exemplo de uso
if __name__ == "__main__":
    import asyncio
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    
    async def test():
        agent = criar_agente_hibrido()
        
        session_service = InMemorySessionService()
        runner = Runner(agent=agent, session_service=session_service)
        
        session = session_service.create_session(
            app_name="suporte_hibrido",
            user_id="test"
        )
        
        # Teste com feedback negativo
        feedback = "Estou muito frustrado! O sistema está péssimo, lento demais!"
        
        print(f"👤 Cliente: {feedback}\n")
        print("🤖 Analisando sentimento e consultando KB...\n")
        
        events = []
        async for event in runner.run_async(
            user_id="test",
            session_id=session.id,
            new_message=feedback
        ):
            events.append(event)
        
        if events:
            print(f"🤖 Resposta: {events[-1].content}")
    
    asyncio.run(test())
