"""
Payoff Calculator for Single Underlying Phoenix Products
=========================================================
Handles Phoenix Snowball structures with one underlying asset.

Example: BNP Phoenix Snowball on S&P 500
"""
from typing import Dict, List, Tuple
import numpy as np


class SinglePhoenixPayoff:
    """
    Payoff calculator for Phoenix products with single underlying
    
    Features:
    - Conditional coupon with memory
    - Autocall (early redemption)
    - Knock-in barrier for principal protection
    """
    
    def __init__(self, payoff_data: Dict):
        """
        Initialize from extracted term sheet data
        
        Args:
            payoff_data: Output from payoff_ready_validator
        """
        self.payoff_data = payoff_data
        self._parse_parameters()
    
    def _parse_parameters(self):
        """Extract and validate parameters from payoff data"""
        # Underlying
        underlyings = self.payoff_data.get("underlyings", [])
        if len(underlyings) != 1:
            raise ValueError(f"Single underlying expected, got {len(underlyings)}")
        
        self.underlying = underlyings[0]
        self.initial_price = self.underlying.get("initial_price")
        
        if not self.initial_price:
            raise ValueError("Missing initial_price for underlying")
        
        # Dates
        dates = self.payoff_data.get("dates", {})
        self.observation_dates = dates.get("observation_dates", [])
        self.valuation_date = dates.get("valuation_date")
        
        if not self.observation_dates:
            raise ValueError("Missing observation_dates")
        
        # Conditional coupon
        coupons = self.payoff_data.get("conditional_coupons", [])
        if not coupons:
            raise ValueError("Missing conditional_coupons")
        
        coupon = coupons[0]
        self.coupon_rate = self._parse_rate(coupon.get("rate", "0%"))
        self.coupon_barrier = self._parse_barrier(coupon.get("barrier_level", "0%"))
        self.has_memory = coupon.get("memory_feature", False)
        
        # Autocall
        autocall = self.payoff_data.get("autocall", {})
        if autocall:
            self.autocall_barrier = self._parse_barrier(autocall.get("barrier_level", "100%"))
            self.has_autocall = True
        else:
            self.autocall_barrier = None
            self.has_autocall = False
        
        # Knock-in
        knock_in = self.payoff_data.get("knock_in", {})
        if knock_in:
            self.knock_in_barrier = self._parse_barrier(knock_in.get("barrier_level", "0%"))
            self.knock_in_type = knock_in.get("type", "European")
        else:
            self.knock_in_barrier = 0.0
            self.knock_in_type = "European"
        
        # Denomination (default to 1000 if not specified)
        product_details = self.payoff_data.get("product_details", {})
        self.denomination = product_details.get("denomination", 1000)
    
    @staticmethod
    def _parse_rate(rate_str: str) -> float:
        """Convert rate string to float: '2.60%' -> 0.026"""
        if isinstance(rate_str, (int, float)):
            return float(rate_str)
        return float(rate_str.strip('%')) / 100.0
    
    @staticmethod
    def _parse_barrier(barrier_str: str) -> float:
        """Convert barrier string to decimal: '70%' -> 0.70"""
        if isinstance(barrier_str, (int, float)):
            return float(barrier_str)
        return float(barrier_str.strip('%')) / 100.0
    
    def calculate_payoff(
        self,
        price_path: List[float],
        denomination: float = None
    ) -> Tuple[float, float, Dict]:
        """
        Calculate total coupons and final payoff for a price path
        
        Args:
            price_path: List of underlying prices at each observation date
            denomination: Investment amount (defaults to term sheet value)
            
        Returns:
            (total_coupons, final_payoff, details)
        """
        if denomination is None:
            denomination = self.denomination
        
        if len(price_path) < len(self.observation_dates):
            raise ValueError(
                f"Price path too short: got {len(price_path)}, "
                f"expected {len(self.observation_dates)}"
            )
        
        total_coupons = 0.0
        accrued_coupons = 0.0
        autocall_triggered = False
        autocall_date = None
        coupon_payments = []
        knock_in_event = False
        
        # Observation loop
        for i, (date, price) in enumerate(zip(self.observation_dates, price_path)):
            performance = price / self.initial_price
            
            # Accrue coupon
            coupon_amount = self.coupon_rate * denomination
            accrued_coupons += coupon_amount
            
            # Check coupon barrier (Phoenix condition)
            if performance >= self.coupon_barrier:
                # Pay out accrued coupons
                total_coupons += accrued_coupons
                coupon_payments.append({
                    "date": date,
                    "amount": accrued_coupons,
                    "performance": performance
                })
                accrued_coupons = 0.0
            
            # Check autocall barrier
            if self.has_autocall and performance >= self.autocall_barrier:
                # Early redemption triggered
                total_coupons += accrued_coupons  # Pay remaining accrued
                autocall_triggered = True
                autocall_date = date
                final_payoff = denomination
                break
            
            # Check knock-in (American style: any observation)
            if self.knock_in_type == "American" and performance < self.knock_in_barrier:
                knock_in_event = True
        
        # If not autocalled, evaluate at maturity
        if not autocall_triggered:
            final_price = price_path[len(self.observation_dates) - 1]
            final_performance = final_price / self.initial_price
            
            # Check knock-in (European style: only at valuation date)
            if self.knock_in_type == "European" and final_performance < self.knock_in_barrier:
                knock_in_event = True
            
            # Determine final payoff
            if knock_in_event:
                # Principal at risk
                final_payoff = denomination * max(final_performance, 0.0)
            else:
                # Principal protected
                final_payoff = denomination
        
        details = {
            "total_coupons": total_coupons,
            "final_payoff": final_payoff,
            "autocall_triggered": autocall_triggered,
            "autocall_date": autocall_date,
            "knock_in_event": knock_in_event,
            "coupon_payments": coupon_payments,
            "accrued_unpaid": accrued_coupons if not autocall_triggered else 0.0
        }
        
        return total_coupons, final_payoff, details
    
    def monte_carlo_valuation(
        self,
        num_simulations: int = 10000,
        price_paths: np.ndarray = None,
        discount_rate: float = 0.0
    ) -> Dict:
        """
        Monte Carlo valuation (requires price paths or simulation engine)
        
        Args:
            num_simulations: Number of Monte Carlo paths
            price_paths: Pre-generated price paths [num_sims, num_obs]
            discount_rate: Risk-free rate for discounting
            
        Returns:
            Dictionary with valuation results
        """
        if price_paths is None:
            raise ValueError("Price paths must be provided for MC simulation")
        
        if price_paths.shape[1] != len(self.observation_dates):
            raise ValueError(
                f"Price paths have {price_paths.shape[1]} points, "
                f"but {len(self.observation_dates)} observation dates"
            )
        
        total_coupons_array = []
        final_payoffs_array = []
        autocall_count = 0
        
        for i in range(num_simulations):
            path = price_paths[i, :]
            coupons, payoff, details = self.calculate_payoff(path)
            
            total_coupons_array.append(coupons)
            final_payoffs_array.append(payoff)
            
            if details["autocall_triggered"]:
                autocall_count += 1
        
        total_coupons_array = np.array(total_coupons_array)
        final_payoffs_array = np.array(final_payoffs_array)
        total_values = total_coupons_array + final_payoffs_array
        
        return {
            "mean_value": np.mean(total_values),
            "std_value": np.std(total_values),
            "mean_coupons": np.mean(total_coupons_array),
            "mean_payoff": np.mean(final_payoffs_array),
            "autocall_probability": autocall_count / num_simulations,
            "value_percentiles": {
                "5%": np.percentile(total_values, 5),
                "25%": np.percentile(total_values, 25),
                "50%": np.percentile(total_values, 50),
                "75%": np.percentile(total_values, 75),
                "95%": np.percentile(total_values, 95)
            }
        }


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Example: Load from extracted term sheet
    import json
    
    # Simulate payoff data (normally from validator)
    example_payoff_data = {
        "structure_type": "single",
        "underlyings": [{
            "name": "S&P 500",
            "ticker": "SPX Index",
            "initial_price": 1985.54
        }],
        "dates": {
            "observation_dates": [
                "2015-03-12", "2015-09-14", "2016-03-14",
                "2016-09-12", "2017-03-13", "2017-09-12"
            ],
            "valuation_date": "2022-09-12"
        },
        "conditional_coupons": [{
            "rate": "2.60%",
            "barrier_level": "70%",
            "memory_feature": True
        }],
        "autocall": {
            "barrier_level": "110%"
        },
        "knock_in": {
            "type": "European",
            "barrier_level": "70%"
        },
        "product_details": {
            "denomination": 1000
        }
    }
    
    # Initialize calculator
    calc = SinglePhoenixPayoff(example_payoff_data)
    
    # Example price path (6 observations)
    price_path = [2100, 2200, 2300, 2400, 2500, 2600]
    
    # Calculate payoff
    coupons, payoff, details = calc.calculate_payoff(price_path)
    
    print("=" * 60)
    print("Single Underlying Phoenix - Payoff Calculation")
    print("=" * 60)
    print(f"Underlying: {calc.underlying['name']}")
    print(f"Initial Price: {calc.initial_price}")
    print(f"Denomination: {calc.denomination}")
    print(f"\nBarriers:")
    print(f"  Coupon: {calc.coupon_barrier:.1%}")
    print(f"  Autocall: {calc.autocall_barrier:.1%}")
    print(f"  Knock-in: {calc.knock_in_barrier:.1%}")
    print(f"\nResults:")
    print(f"  Total Coupons: ${coupons:.2f}")
    print(f"  Final Payoff: ${payoff:.2f}")
    print(f"  Total Value: ${coupons + payoff:.2f}")
    print(f"  Autocall: {details['autocall_triggered']}")
    if details['autocall_triggered']:
        print(f"  Autocall Date: {details['autocall_date']}")
    print("=" * 60)

