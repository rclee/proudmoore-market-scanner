import unittest
from datetime import datetime, timezone, timedelta
from scanner.__main__ import load_config
from scanner.trading import trading_plan
from pathlib import Path

NOW=datetime(2026,10,31,18,0,tzinfo=timezone.utc)
class TradingPlan(unittest.TestCase):
    def fixture(self):
        config=load_config(Path(__file__).resolve().parents[1]/'config.json')
        row={'item_id':1,'name':'Liquid test commodity','scope':'commodities','regional_source_time':NOW.isoformat(),
            'source_time':NOW.isoformat(),'regional_sold_per_day':'10000','regional_sale_rate':'0.4','conservative_resale_copper':1000000}
        report={'mode':'live','status':'watch_only','config':config,'watchlist':[row]}
        detail={'item_id':1,'status':'fresh','total_quantity':100000,'observed_at':NOW.isoformat(),
                'median_copper':1200000,'unit_price_copper':700000,
                'history':[{'at':(NOW-timedelta(hours=i)).isoformat(),'median_copper':1200000} for i in range(1,49)]}
        return report,{'commodity_details':[detail]}
    def test_200k_policy_produces_bounded_quote_and_exit_prices(self):
        report,extra=self.fixture();plan=trading_plan(report,extra,NOW)
        self.assertEqual(plan['policy']['bankroll_copper'],2000000000)
        self.assertEqual(plan['policy']['reserve_copper'],400000000)
        self.assertEqual(plan['status'],'collect_quotes')
        task=plan['quote_checks'][0]
        self.assertLessEqual(task['quantity'],200)
        self.assertLessEqual(task['maximum_total_copper'],200000000)
        self.assertGreaterEqual(task['projected_profit_at_cap_copper'],1000000)
        self.assertFalse(task['sale_guaranteed'])
        self.assertTrue(task['quote_required'])
        self.assertEqual(task['posting_duration_hours'],12)
    def test_low_demand_and_stale_snapshots_do_not_become_trade_tasks(self):
        report,extra=self.fixture();report['watchlist'][0]['regional_sold_per_day']='1'
        self.assertEqual(trading_plan(report,extra,NOW)['quote_checks'],[])
        report,extra=self.fixture();extra['commodity_details'][0]['observed_at']=(NOW-timedelta(hours=3)).isoformat()
        self.assertEqual(trading_plan(report,extra,NOW)['quote_checks'],[])
    def test_combined_quote_ceiling_fits_session_budget(self):
        report,extra=self.fixture()
        for item in range(2,6):
            report['watchlist'].append({**report['watchlist'][0],'item_id':item})
            extra['commodity_details'].append({**extra['commodity_details'][0],'item_id':item})
        tasks=trading_plan(report,extra,NOW)['quote_checks']
        self.assertLessEqual(len(tasks),3)
        self.assertLessEqual(sum(row['maximum_total_copper'] for row in tasks),400000000)
    def test_high_snapshot_price_is_a_data_check_never_a_buy(self):
        report,extra=self.fixture();extra['commodity_details'][0]['unit_price_copper']=2000000
        task=trading_plan(report,extra,NOW)['quote_checks'][0]
        self.assertFalse(task['snapshot_within_limit'])
        self.assertTrue(task['quote_required'])

if __name__=='__main__':unittest.main()
