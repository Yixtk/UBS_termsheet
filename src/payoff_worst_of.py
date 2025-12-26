"""
Payoff Calculator for Worst-of Phoenix Products
================================================
Handles Phoenix products with multiple underlyings where payoff depends on
the worst-performing asset.

Example: Natixis Phoenix on AMD/NVDA/INTC
"""
from typing import Dict, List, Tuple
import numpy as np


class WorstOfPhoenixPayoff:
    """
    Payoff calculator for Phoenix products with multiple underlyings (worst-of)
    
    Features:
    - Fixed coupon (optional, paid once)
    - Conditional coupon with memory (based on worst performer)
    - Autocall (early redemption based on worst performer)
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
        # Underlyings
        underlyings = self.payoff_data.get("underlyings", [])
        if len(underlyings) < 2:
            raise ValueError(f"Worst-of requires 2+ underlyings, got {len(underlyings)}")
        
        self.underlyings = underlyings
        self.num_underlyings = len(underlyings)
        self.initial_prices = [u.get("initial_price") for u in underlyings]
        
        if any(p is None for p in self.initial_prices):
            raise ValueError("Missing initial_price for one or more underlyings")
        
        # Dates
        dates = self.payoff_data.get("dates", {})
        self.observation_dates = dates.get("observation_dates", [])
        self.valuation_date = dates.get("valuation_date")
        
        if not self.observation_dates:
            raise ValueError("Missing observation_dates")
        
        # Fixed coupon (if any)
        fixed_coupon = self.payoff_data.get("fixed_coupon", {})
        if fixed_coupon:
            self.fixed_coupon_rate = self._parse_rate(fixed_coupon.get("rate", "0%"))
            self.has_fixed_coupon = True
        else:
            self.fixed_coupon_rate = 0.0
            self.has_fixed_coupon = False
        
        # Conditional coupon
        coupons = self.payoff_data.get("conditional_coupons", [])
        if not coupons:
            raise ValueError("Missing conditional_coupons")
        
        # Find the main conditional coupon (with trigger condition)
        main_coupon = None
        for coupon in coupons:
            if "trigger_condition" in coupon and coupon.get("trigger_condition"):
                main_coupon = coupon
                break
        
        if not main_coupon:
            main_coupon = coupons[0]
        
        # Parse coupon rate (handle monthly rate format like "0.3333% x t")
        rate_str = main_coupon.get("rate") or main_coupon.get("calculation_formula", "0%")
        self.coupon_rate = self._parse_monthly_rate(rate_str)
        
        # Parse barrier (might be in different coupons)
        barrier_level = None
        for coupon in coupons:
            if coupon.get("barrier_level"):
                barrier_level = coupon.get("barrier_level")
                break
        
        self.coupon_barrier = self._parse_barrier(barrier_level or "50%")
        self.has_memory = main_coupon.get("memory_feature", False)
        
        # Autocall
        autocall = self.payoff_data.get("autocall", {})
        if autocall:
            self.autocall_barrier = self._parse_barrier(autocall.get("barrier_level", "100%"))
            self.has_autocall = True
        else:
            self.autocall_barrier = None
            self.has_autocall = False
        
        # Knock-in - use barrier_prices if available (more reliable than barrier_level)
        knock_in = self.payoff_data.get("knock_in", {})
        if knock_in:
            # Try to calculate barrier from barrier_prices (most reliable)
            barrier_prices = knock_in.get("barrier_prices", [])
            if barrier_prices and len(barrier_prices) > 0:
                # Calculate implied barrier from first underlying
                first_barrier = barrier_prices[0]
                ki_price = first_barrier.get("knock_in_price") or first_barrier.get("barrier_price")
                if ki_price and len(self.initial_prices) > 0:
                    # Find matching underlying
                    underlying_name = first_barrier.get("underlying", "")
                    for i, u in enumerate(self.underlyings):
                        if underlying_name.lower() in u.get("name", "").lower():
                            self.knock_in_barrier = ki_price / self.initial_prices[i]
                            break
                    else:
                        # If no match, use first underlying
                        self.knock_in_barrier = ki_price / self.initial_prices[0]
                else:
                    self.knock_in_barrier = self._parse_barrier(knock_in.get("barrier_level", "50%"))
            else:
                self.knock_in_barrier = self._parse_barrier(knock_in.get("barrier_level", "50%"))
            
            self.knock_in_type = knock_in.get("type", "European")
        else:
            self.knock_in_barrier = 0.0
            self.knock_in_type = "European"
        
        # Denomination
        product_details = self.payoff_data.get("product_details", {})
        self.denomination = product_details.get("denomination", 1000)
    
    @staticmethod
    def _parse_rate(rate_str: str) -> float:
        """Convert rate string to float: '19.00%' -> 0.19"""
        if isinstance(rate_str, (int, float)):
            return float(rate_str)
        return float(str(rate_str).strip('%')) / 100.0
    
    @staticmethod
    def _parse_monthly_rate(rate_str: str) -> float:
        """
        Parse monthly rate from formula
        Examples: '0.3333%', '0.3333% x t' -> 0.003333 per month
        """
        if isinstance(rate_str, (int, float)):
            return float(rate_str)
        
        # Extract number before %
        import re
        match = re.search(r'([\d.]+)\s*%', str(rate_str))
        if match:
            return float(match.group(1)) / 100.0
        
        return 0.0
    
    @staticmethod
    def _parse_barrier(barrier_str: str) -> float:
        """Convert barrier string to decimal: '50%' -> 0.50"""
        if isinstance(barrier_str, (int, float)):
            return float(barrier_str)
        return float(str(barrier_str).strip('%').strip()) / 100.0
    
    def calculate_payoff(
        self,
        price_paths: List[List[float]],
        denomination: float = None
    ) -> Tuple[float, float, Dict]:
        """
        Calculate total coupons and final payoff for multiple price paths
        
        Args:
            price_paths: List of price paths, one per underlying
                        [[underlying1_prices], [underlying2_prices], ...]
            denomination: Investment amount (defaults to term sheet value)
            
        Returns:
            (total_coupons, final_payoff, details)
        """
        if denomination is None:
            denomination = self.denomination
        
        if len(price_paths) != self.num_underlyings:
            raise ValueError(
                f"Expected {self.num_underlyings} price paths, got {len(price_paths)}"
            )
        
        num_observations = len(self.observation_dates)
        
        for i, path in enumerate(price_paths):
            if len(path) < num_observations:
                raise ValueError(
                    f"Price path {i} too short: got {len(path)}, expected {num_observations}"
                )
        
        # Fixed coupon (paid once at issuance)
        fixed_coupon_paid = 0.0
        if self.has_fixed_coupon:
            fixed_coupon_paid = self.fixed_coupon_rate * denomination
        
        # Conditional coupons (memory feature)
        conditional_coupons_paid = 0.0
        accrued_coupons = 0.0
        autocall_triggered = False
        autocall_date = None
        coupon_payments = []
        knock_in_event = False
        
        # Observation loop
        for obs_idx in range(num_observations):
            # Get prices at this observation
            current_prices = [path[obs_idx] for path in price_paths]
            
            # Calculate performances
            performances = [
                current_prices[i] / self.initial_prices[i]
                for i in range(self.num_underlyings)
            ]
            worst_performance = min(performances)
            
            # Accrue monthly coupon
            coupon_amount = self.coupon_rate * denomination
            accrued_coupons += coupon_amount
            
            # Check Phoenix barrier (worst-of condition)
            if worst_performance >= self.coupon_barrier:
                # Pay out all accrued coupons (memory feature)
                conditional_coupons_paid += accrued_coupons
                coupon_payments.append({
                    "date": self.observation_dates[obs_idx],
                    "amount": accrued_coupons,
                    "worst_performance": worst_performance
                })
                accrued_coupons = 0.0
            
            # Check autocall barrier
            if self.has_autocall and worst_performance >= self.autocall_barrier:
                # Early redemption triggered
                conditional_coupons_paid += accrued_coupons  # Pay remaining accrued
                autocall_triggered = True
                autocall_date = self.observation_dates[obs_idx]
                final_payoff = denomination
                break
            
            # Check knock-in (American: any breach triggers)
            if self.knock_in_type == "American" and worst_performance < self.knock_in_barrier:
                knock_in_event = True
        
        # If not autocalled, evaluate at maturity
        if not autocall_triggered:
            # Final observation
            final_prices = [path[num_observations - 1] for path in price_paths]
            final_performances = [
                final_prices[i] / self.initial_prices[i]
                for i in range(self.num_underlyings)
            ]
            worst_final_performance = min(final_performances)
            
            # Check knock-in (European: only at valuation)
            if self.knock_in_type == "European" and worst_final_performance < self.knock_in_barrier:
                knock_in_event = True
            
            # Determine final payoff
            if knock_in_event:
                # Principal at risk - worst performer determines payoff
                final_payoff = denomination * max(worst_final_performance, 0.0)
            else:
                # Principal protected
                final_payoff = denomination
        
        # Calculate totals
        total_coupons = fixed_coupon_paid + conditional_coupons_paid
        
        details = {
            "fixed_coupon": fixed_coupon_paid,
            "conditional_coupons": conditional_coupons_paid,
            "total_coupons": total_coupons,
            "final_payoff": final_payoff,
            "total_value": total_coupons + final_payoff,
            "autocall_triggered": autocall_triggered,
            "autocall_date": autocall_date,
            "knock_in_event": knock_in_event,
            "coupon_payments": coupon_payments,
            "accrued_unpaid": accrued_coupons if not autocall_triggered else 0.0,
            "num_coupon_payments": len(coupon_payments),
            "num_conditional_coupon_payments": len(coupon_payments)
        }
        
        return total_coupons, final_payoff, details
    
    def monte_carlo_valuation(
        self,
        num_simulations: int = 10000,
        price_paths: np.ndarray = None,
        discount_rate: float = 0.0
    ) -> Dict:
        """
        Monte Carlo valuation
        
        Args:
            num_simulations: Number of MC paths
            price_paths: Pre-generated paths [num_sims, num_underlyings, num_obs]
            discount_rate: Risk-free rate for discounting
            
        Returns:
            Dictionary with valuation results
        """
        if price_paths is None:
            raise ValueError("Price paths must be provided for MC simulation")
        
        if price_paths.shape[1] != self.num_underlyings:
            raise ValueError(
                f"Expected {self.num_underlyings} underlyings, "
                f"got {price_paths.shape[1]}"
            )
        
        if price_paths.shape[2] != len(self.observation_dates):
            raise ValueError(
                f"Expected {len(self.observation_dates)} observations, "
                f"got {price_paths.shape[2]}"
            )
        
        total_coupons_array = []
        final_payoffs_array = []
        autocall_count = 0
        
        for i in range(num_simulations):
            # Extract paths for all underlyings
            paths = [price_paths[i, j, :] for j in range(self.num_underlyings)]
            
            coupons, payoff, details = self.calculate_payoff(paths)
            
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
    # Example: Worst-of Phoenix on 3 stocks
    example_payoff_data = {
        "structure_type": "worst_of",
        "underlyings": [
            {"name": "AMD", "ticker": "AMD UW", "initial_price": 140.75},
            {"name": "NVIDIA", "ticker": "NVDA UW", "initial_price": 118.08},
            {"name": "Intel", "ticker": "INTC UW", "initial_price": 19.92}
        ],
        "dates": {
            "observation_dates": [
                "2024-10-07", "2024-11-07", "2024-12-09",
                "2025-01-07", "2025-02-07", "2025-03-07"
            ],
            "valuation_date": "2027-08-09"
        },
        "fixed_coupon": {
            "rate": "19.00%"
        },
        "conditional_coupons": [{
            "rate": "0.3333%",
            "barrier_level": "50%",
            "memory_feature": True
        }],
        "autocall": {
            "barrier_level": "100%"
        },
        "knock_in": {
            "type": "European",
            "barrier_level": "50%"
        },
        "product_details": {
            "denomination": 1000
        }
    }
    
    # Initialize calculator
    calc = WorstOfPhoenixPayoff(example_payoff_data)
    
    # Example price paths (3 underlyings, 6 observations)
    # Scenario: All perform well, autocall triggers
    price_paths = [
        [150, 160, 170, 180, 190, 200],  # AMD
        [130, 140, 150, 160, 170, 180],  # NVIDIA
        [22, 24, 26, 28, 30, 32]          # Intel
    ]
    
    # Calculate payoff
    coupons, payoff, details = calc.calculate_payoff(price_paths)
    
    print("=" * 60)
    print("Worst-of Phoenix - Payoff Calculation")
    print("=" * 60)
    print(f"Underlyings: {calc.num_underlyings}")
    for u in calc.underlyings:
        print(f"  - {u['name']}: {u['initial_price']}")
    print(f"Denomination: {calc.denomination}")
    print(f"\nBarriers:")
    print(f"  Coupon (Phoenix): {calc.coupon_barrier:.1%}")
    print(f"  Autocall: {calc.autocall_barrier:.1%}")
    print(f"  Knock-in: {calc.knock_in_barrier:.1%}")
    print(f"\nCoupon Structure:")
    if calc.has_fixed_coupon:
        print(f"  Fixed: {calc.fixed_coupon_rate:.2%} = ${calc.fixed_coupon_rate * calc.denomination:.2f}")
    print(f"  Monthly: {calc.coupon_rate:.4%} per month")
    print(f"  Memory: {calc.has_memory}")
    print(f"\nResults:")
    print(f"  Total Coupons: ${coupons:.2f}")
    print(f"  Final Payoff: ${payoff:.2f}")
    print(f"  Total Value: ${coupons + payoff:.2f}")
    print(f"  Return: {((coupons + payoff) / calc.denomination - 1) * 100:.2f}%")
    print(f"  Autocall: {details['autocall_triggered']}")
    if details['autocall_triggered']:
        print(f"  Autocall Date: {details['autocall_date']}")
    print(f"  Coupon Payments: {details['num_coupon_payments']}")
    print("=" * 60)

