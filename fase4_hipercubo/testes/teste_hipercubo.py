"""Testes da fase 4. Rodar: uv run python -m fase4_hipercubo.testes.teste_hipercubo

Sem pytest (como as demais fases): cada modulo tem _teste() com assert.
"""
from fase4_hipercubo.modelo import hc_real, hipercubo_aprox, hipercubo_exato

if __name__ == "__main__":
    hipercubo_exato._teste()
    hipercubo_aprox._teste()
    hc_real._teste()
    print("fase 4: todos os testes ok")
