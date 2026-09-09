from decimal import Decimal
from typing import List, Dict
from database.models import Transaction, TransactionType


def calculate_investment_metrics(transactions: List[Transaction]) -> Dict:
    """
    Calcula as métricas de um investimento baseado no histórico cronológico de transações.
    
    Retorna um dicionário contendo:
    - open_quantity: quantidade de cotas da posição em aberto (Decimal)
    - open_cost: custo total investido na posição em aberto (Decimal)
    - average_price: preço médio de aquisição da posição em aberto (Decimal)
    - last_pm: último preço médio calculado (mesmo se a posição estiver zerada) (Decimal)
    - total_realized_profit: lucro total realizado com vendas (Decimal)
    - transaction_details: dict mapeando transaction_id -> {
          'cost_basis': Decimal,
          'realized_profit': Decimal,
          'profit_pct': Decimal,
          'pm_at_transaction': Decimal
      }
    """
    if not transactions:
        return {
            'open_quantity': Decimal('0'),
            'open_cost': Decimal('0'),
            'average_price': Decimal('0'),
            'last_pm': Decimal('0'),
            'total_realized_profit': Decimal('0'),
            'transaction_details': {}
        }

    sorted_txs = sorted(transactions, key=lambda t: (t.date, t.id))
    
    running_qty = Decimal('0')
    running_cost = Decimal('0')
    last_pm = Decimal('0')
    total_realized_profit = Decimal('0')
    tx_details = {}
    
    for t in sorted_txs:
        qty = t.quantity or Decimal('0')
        price = t.price_per_unit or Decimal('0')
        amount = t.amount if t.amount is not None else (qty * price)
        
        if t.transaction_type == TransactionType.EXPENSE:  # Compra
            running_qty += qty
            running_cost += amount
            if running_qty > 0:
                last_pm = running_cost / running_qty
            tx_details[t.id] = {
                'cost_basis': amount,
                'realized_profit': Decimal('0'),
                'profit_pct': Decimal('0'),
                'pm_at_transaction': last_pm
            }
        elif t.transaction_type == TransactionType.INCOME:  # Venda
            cost_basis = qty * last_pm
            realized_profit = amount - cost_basis
            profit_pct = (realized_profit / cost_basis * 100) if cost_basis > 0 else Decimal('0')
            
            tx_details[t.id] = {
                'cost_basis': cost_basis,
                'realized_profit': realized_profit,
                'profit_pct': profit_pct,
                'pm_at_transaction': last_pm
            }
            
            total_realized_profit += realized_profit
            running_cost = max(Decimal('0'), running_cost - cost_basis)
            running_qty = max(Decimal('0'), running_qty - qty)
            if running_qty > 0:
                last_pm = running_cost / running_qty
                
    return {
        'open_quantity': running_qty,
        'open_cost': running_cost,
        'average_price': last_pm if running_qty > 0 else Decimal('0'),
        'last_pm': last_pm,
        'total_realized_profit': total_realized_profit,
        'transaction_details': tx_details
    }
