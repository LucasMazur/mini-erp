
from fractions import Fraction


def calculate_proportional_cost_cents(
    purchase_total_cents: int,
    purchased_quantity_milli: int,
    consumed_quantity_milli: int,
) -> int:
    """
    Calcula o custo proporcional de uma quantidade consumida.

    Todas as quantidades devem estar na mesma unidade-base,
    expressas em milésimos dessa unidade.

    O arredondamento acontece somente no resultado final,
    para o centavo mais próximo.
    """

    if purchase_total_cents < 0:
        raise ValueError("O valor da compra não pode ser negativo.")

    if purchased_quantity_milli <= 0:
        raise ValueError("A quantidade comprada deve ser positiva.")

    if consumed_quantity_milli < 0:
        raise ValueError("O consumo não pode ser negativo.")

    exact_cost = Fraction(
        purchase_total_cents * consumed_quantity_milli,
        purchased_quantity_milli,
    )

    # Arredondamento para o centavo mais próximo.
    return (
        2 * exact_cost.numerator + exact_cost.denominator
    ) // (2 * exact_cost.denominator)
