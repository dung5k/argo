import os
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.bot_v2.trade_manager_v2 import V2TradeManager

class TestV2TradeManager(unittest.TestCase):

    def setUp(self):
        self.config = {
            "LIVE_TRADING": {
                "BUY_ENTRY_THR": 0.60,
                "SELL_ENTRY_THR": 0.40,
                "CLOSE_BUY_THR": 0.50,
                "CLOSE_SELL_THR": 0.50,
                "lot_size": 0.1
            }
        }
        self.manager = V2TradeManager(target_symbol="XAUUSD", config=self.config, log_callback=lambda x: None)
        self.manager.mt5 = MagicMock()
        
        # Setup constants for MT5 mock
        self.manager.mt5.ORDER_TYPE_BUY = 0
        self.manager.mt5.ORDER_TYPE_SELL = 1
        self.manager.mt5.TRADE_RETCODE_DONE = 10009

    def test_open_new_mt5_trade_buy(self):
        # 1. Setup mocks
        mock_point = MagicMock(point=0.01)
        self.manager.mt5.symbol_info.return_value = mock_point
        
        mock_tick = MagicMock(ask=2000.50, bid=2000.00)
        self.manager.mt5.symbol_info_tick.return_value = mock_tick
        
        mock_result = MagicMock(retcode=10009, order=123456)
        self.manager.mt5.order_send.return_value = mock_result
        
        # 2. Execution
        ticket = self.manager.open_new_mt5_trade("XAUUSD", self.manager.mt5.ORDER_TYPE_BUY, 0.1, 50, 100, 0.85)
        
        # 3. Validation
        self.assertEqual(ticket, 123456)
        self.manager.mt5.order_send.assert_called_once()
        args, kwargs = self.manager.mt5.order_send.call_args
        request = args[0]
        self.assertEqual(request["type"], self.manager.mt5.ORDER_TYPE_BUY)
        self.assertEqual(request["price"], 2000.50)
        
    def test_manage_mt5_positions_no_open_shoot_sell(self):
        # Setup no open positions
        self.manager.mt5.positions_get.return_value = ()
        
        # Intercept open_new_mt5_trade
        self.manager.open_new_mt5_trade = MagicMock()
        
        # Prob = 0.20 -> SHOULD OPEN SELL
        self.manager.manage_mt5_positions(0.20)
        
        self.manager.open_new_mt5_trade.assert_called_once()
        args, kwargs = self.manager.open_new_mt5_trade.call_args
        self.assertEqual(args[1], self.manager.mt5.ORDER_TYPE_SELL)

    def test_manage_mt5_positions_close_buy(self):
        # Setup open position
        mock_pos = MagicMock(type=self.manager.mt5.ORDER_TYPE_BUY, ticket=999)
        self.manager.mt5.positions_get.return_value = (mock_pos,)
        
        # Intercept close
        self.manager.close_mt5_position = MagicMock()
        
        # Prob drops to 0.45 (< 0.50 CLOSE_BUY_THR) -> SHOULD CLOSE
        self.manager.manage_mt5_positions(0.45)
        
        self.manager.close_mt5_position.assert_called_once_with(mock_pos)
        self.assertIn("ĐÃ CHỐT BIÊN BUY", self.manager.gui_action)

if __name__ == '__main__':
    unittest.main()
