

class MathUtility():
    @classmethod
    def clamp(cls, param: float, min_value: float, max_value: float) -> float:
        if min_value > max_value:
            raise ValueError('Invaild min value or max value')
        return min(max_value, max(param, min_value))

    @classmethod
    def lerp(cls, a: float, b: float, t: float) -> float:
        return a + (b - a) * t
