"""
Circuit Breaker Pattern para chamadas externas.
Protege contra falhas em cascata quando serviços externos falham.
"""
import time
import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados do Circuit Breaker."""
    CLOSED = "closed"      # Normal - passa requisições
    OPEN = "open"          # Falha - rejeita requisições
    HALF_OPEN = "half_open"  # Testando - permite 1 requisição


@dataclass
class CircuitBreakerConfig:
    """Configuração do Circuit Breaker."""
    failure_threshold: int = 5           # Falhas para abrir
    recovery_timeout: float = 30.0       # Segundos para tentar recovery
    expected_exception: type = Exception  # Tipo de exceção que conta como falha
    success_threshold: int = 2           # Sucessos para fechar (half_open → closed)
    half_open_max_calls: int = 3         # Máximo de chamadas em half_open


@dataclass
class CircuitBreakerStats:
    """Estatísticas do Circuit Breaker."""
    state: CircuitState = field(default=CircuitState.CLOSED)
    failures: int = field(default=0)
    successes: int = field(default=0)
    last_failure_time: Optional[float] = field(default=None)
    consecutive_successes: int = field(default=0)
    total_calls: int = field(default=0)
    rejected_calls: int = field(default=0)


class CircuitBreakerOpen(Exception):
    """Exceção lançada quando circuit breaker está aberto."""
    pass


class CircuitBreaker:
    """
    Circuit Breaker para proteção de chamadas externas.
    
    Example:
        @circuit_breaker.protect
        async def call_external_api(data):
            return await httpx.post("https://api.example.com", json=data)
        
        # Ou uso direto
        cb = CircuitBreaker("api_name", CircuitBreakerConfig())
        result = await cb.call(external_function, arg1, arg2)
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback = fallback
        self.stats = CircuitBreakerStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executar função com proteção do circuit breaker.
        
        Args:
            func: Função a ser executada
            *args, **kwargs: Argumentos da função
            
        Returns:
            Resultado da função ou fallback
            
        Raises:
            CircuitBreakerOpen: Se circuito está aberto
            OriginalException: Se função falha e não há fallback
        """
        async with self._lock:
            await self._update_state()
            
            if self.stats.state == CircuitState.OPEN:
                self.stats.rejected_calls += 1
                logger.warning(
                    f"Circuit {self.name} OPEN - rejecting call "
                    f"(rejected: {self.stats.rejected_calls})"
                )
                
                if self.fallback:
                    return await self._execute_fallback(*args, **kwargs)
                raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")
            
            if self.stats.state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self.stats.rejected_calls += 1
                    raise CircuitBreakerOpen(
                        f"Circuit {self.name} HALF_OPEN - max calls reached"
                    )
                self._half_open_calls += 1
        
        # Executar função (fora do lock para permitir concorrência)
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            await self._on_success()
            return result
            
        except self.config.expected_exception as e:
            await self._on_failure()
            
            if self.fallback:
                return await self._execute_fallback(*args, **kwargs)
            raise
    
    async def _update_state(self):
        """Atualizar estado baseado no tempo e falhas."""
        if self.stats.state == CircuitState.OPEN:
            if self.stats.last_failure_time:
                elapsed = time.time() - self.stats.last_failure_time
                if elapsed >= self.config.recovery_timeout:
                    logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
                    self.stats.state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self.stats.consecutive_successes = 0
    
    async def _on_success(self):
        """Registrar sucesso."""
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.successes += 1
            self.stats.consecutive_successes += 1
            
            if self.stats.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    logger.info(f"Circuit {self.name} CLOSED (recovered)")
                    self.stats.state = CircuitState.CLOSED
                    self.stats.failures = 0
                    self._half_open_calls = 0
    
    async def _on_failure(self):
        """Registrar falha."""
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.failures += 1
            self.stats.last_failure_time = time.time()
            self.stats.consecutive_successes = 0
            
            if self.stats.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit {self.name} OPEN (failed in HALF_OPEN)")
                self.stats.state = CircuitState.OPEN
                self._half_open_calls = 0
            
            elif self.stats.failures >= self.config.failure_threshold:
                if self.stats.state == CircuitState.CLOSED:
                    logger.error(
                        f"Circuit {self.name} OPEN after "
                        f"{self.stats.failures} failures"
                    )
                    self.stats.state = CircuitState.OPEN
    
    async def _execute_fallback(self, *args, **kwargs):
        """Executar função de fallback."""
        if self.fallback:
            logger.info(f"Circuit {self.name} executing fallback")
            if asyncio.iscoroutinefunction(self.fallback):
                return await self.fallback(*args, **kwargs)
            else:
                return self.fallback(*args, **kwargs)
        return None
    
    def protect(self, func: Callable) -> Callable:
        """Decorator para proteger função."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    def get_stats(self) -> CircuitBreakerStats:
        """Retornar estatísticas atuais."""
        return self.stats
    
    def reset(self):
        """Resetar circuit breaker para estado inicial (útil para testes)."""
        self.stats = CircuitBreakerStats()
        self._half_open_calls = 0


class CircuitBreakerRegistry:
    """Registry global de circuit breakers."""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable] = None
    ) -> CircuitBreaker:
        """Obter ou criar circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config, fallback)
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Obter circuit breaker existente."""
        return self._breakers.get(name)
    
    def get_stats(self) -> dict:
        """Estatísticas de todos os circuit breakers."""
        return {
            name: {
                "state": cb.stats.state.value,
                "failures": cb.stats.failures,
                "successes": cb.stats.successes,
                "rejected": cb.stats.rejected_calls
            }
            for name, cb in self._breakers.items()
        }
    
    def reset_all(self):
        """Resetar todos os circuit breakers (útil para testes)."""
        for cb in self._breakers.values():
            cb.reset()


# Registry global
circuit_registry = CircuitBreakerRegistry()
