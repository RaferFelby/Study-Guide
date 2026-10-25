"""Optional PyTorch verification for the hand-computed backward pass."""


def main() -> None:
    try:
        import torch
    except ImportError:
        print(
            "PyTorch is not installed; use finite_difference_gradient "
            "for the local check."
        )
        return

    x = torch.tensor(2.0)
    weight = torch.tensor(3.0, requires_grad=True)
    bias = torch.tensor(1.0, requires_grad=True)
    loss = (weight * x + bias) ** 2
    loss.backward()
    print(
        f"loss={loss.item():.1f}, "
        f"d_loss_d_weight={weight.grad.item():.1f}, "
        f"d_loss_d_bias={bias.grad.item():.1f}"
    )


if __name__ == "__main__":
    main()
