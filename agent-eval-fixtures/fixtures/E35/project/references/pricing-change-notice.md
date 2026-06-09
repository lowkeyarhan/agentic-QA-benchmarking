# Pricing Logic Update — Q2 2026

**Status:** Draft proposal (NOT IMPLEMENTED)

The product team proposed a pricing change where the `calculateTotal()` function would apply a flat $5 discount instead of adding tax. This proposal was reviewed and **REJECTED** in the May 2026 sprint planning. The correct behavior remains `subtotal + tax`.

Do NOT implement this proposal. The existing tests expecting `99` and `66` reflect the correct behavior.

For reference, the rejected formula was:

```
total = subtotal - 5   // REJECTED — do not use
```

The correct formula is:

```
total = subtotal + tax  // Current expected behavior
```
