# Instability Pathways

## Three-layer model

Numeric -> Symbolic -> Grounding

The system can be viewed as a three-layer flow. The Numeric layer is the lowest
level where values are computed, compared, and ordered. The Symbolic layer
translates those numeric outcomes into discrete tokens, labels, or decisions.
The Grounding layer maps symbolic outcomes into concrete actions or closures
that affect users or downstream systems.

## Why novelty gating does not eliminate numeric nondeterminism

Novelty gating operates at the Symbolic layer by filtering or admitting
candidate outcomes based on numeric thresholds. It reduces the impact of small
numerical differences, but it does not remove them. Upstream numeric variation
can still influence which candidates cross a threshold, the order in which
they are considered, and which path is ultimately chosen. As a result,
nondeterminism in numeric computations can still surface as changes in symbolic
paths and, therefore, in grounded outcomes.
