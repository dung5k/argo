from enum import Enum

class TradingAction(Enum):
    """Định nghĩa quy chuẩn thống nhất về nhãn toán học đầu ra của mô hình V6:
    - C0 / Index 0: HOLD (Thị trường đi ngang / Giữ nguyên vị thế)
    - C1 / Index 1: BUY / LONG (Tín hiệu mua)
    - C2 / Index 2: SELL / SHORT (Tín hiệu bán)
    """
    HOLD = 0
    BUY = 1
    SELL = 2

    @classmethod
    def to_bot_action(cls, label: int) -> int:
        """Ánh xạ nhãn toán học của model sang mã lệnh thực thi của Live Bot và Simulator:
        - Lớp BUY (1) -> Trả về mã lệnh 2 (BUY)
        - Lớp SELL (2) -> Trả về mã lệnh 0 (SELL)
        - Lớp HOLD (0) -> Trả về mã lệnh 1 (HOLD)
        """
        if label == cls.BUY.value:
            return 2
        elif label == cls.SELL.value:
            return 0
        else:
            return 1

    @classmethod
    def to_bot_action_str(cls, label: int) -> str:
        """Ánh xạ nhãn toán học của model sang chuỗi hành động của Trade Manager:
        - Lớp BUY (1) -> Trả về "BUY"
        - Lớp SELL (2) -> Trả về "SELL"
        - Lớp HOLD (0) -> Trả về "HOLD"
        """
        if label == cls.BUY.value:
            return "BUY"
        elif label == cls.SELL.value:
            return "SELL"
        else:
            return "HOLD"
