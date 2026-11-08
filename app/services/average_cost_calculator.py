from fractions import Fraction


def calculate_weighted_average_cost(
    current_quantity_milli: int,
    current_value_cents: int,
    incoming_quantity_milli: int,
    incoming_value_cents: int,
) -> Fraction:
    """
    Retorna o custo médio em centavos por milésimo
    da unidade de estoque.
    """

    values = (
        current_quantity_milli,
        current_value_cents,
        incoming_quantity_milli,
        incoming_value_cents,
    )

    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        raise ValueError("Os valores devem ser números inteiros.")

    if current_quantity_milli < 0 or incoming_quantity_milli < 0:
        raise ValueError("As quantidades não podem ser negativas.")

    if current_value_cents < 0 or incoming_value_cents < 0:
        raise ValueError("Os valores não podem ser negativos.")

    total_quantity = current_quantity_milli + incoming_quantity_milli
    total_value = current_value_cents + incoming_value_cents

    if total_quantity == 0:
        if total_value != 0:
            raise ValueError("Não pode existir valor sem quantidade em estoque.")
        return Fraction(0)

    return Fraction(total_value, total_quantity)


def calculate_consumption_cost_cents(
    current_quantity_milli: int,
    current_value_cents: int,
    consumed_quantity_milli: int,
) -> int:
    """Calcula o custo de uma saída pelo custo médio vigente."""

    if current_quantity_milli <= 0:
        raise ValueError("Não existe estoque disponível.")

    if consumed_quantity_milli < 0:
        raise ValueError("A quantidade consumida não pode ser negativa.")

    if consumed_quantity_milli > current_quantity_milli:
        raise ValueError("Consumo maior que o estoque disponível.")

    average_cost = Fraction(
        current_value_cents,
        current_quantity_milli,
    )

    exact_cost = average_cost * consumed_quantity_milli

    # Arredondamento para o centavo mais próximo, meio para cima.
    return (
        2 * exact_cost.numerator + exact_cost.denominator
    ) // (2 * exact_cost.denominator)