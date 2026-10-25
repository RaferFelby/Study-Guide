"""在本工程运行：python distribution_demo.py。"""

from statistics import NormalDist

from app.distributions import binomial_probability, summarize_population


def main() -> None:
    for successes in range(4):
        print(successes, binomial_probability(3, successes, 0.5))
    print(summarize_population([8, 8, 12, 12]))
    print(summarize_population([6, 6, 14, 14]))
    model = NormalDist(mu=10, sigma=2)
    print(model.cdf(12) - model.cdf(8))


if __name__ == "__main__":
    main()
