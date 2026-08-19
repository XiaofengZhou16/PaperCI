# Mechanistic-biology profile

Create the profile with:

```bash
paperci init study --profile mechanistic-biology
```

The resulting project contains no evidence, claim, or synthetic result. Its
`org.paperci.profile.v1` extension provides six review prompts:

1. bounded observation;
2. intervention testing necessity, sufficiency, or direction;
3. target engagement;
4. route-discriminating rescue or reversal;
5. orthogonal evidence;
6. independent parent units for nested cells, wells, organoids, lesions, or images.

This is a workflow scaffold, not a universal sufficiency checklist. Some mechanisms
need direct binding, structural, temporal, lineage, mediation, or other domain-specific
evidence. Conversely, not every project needs every prompt. The claim must remain
bounded to the tested biological scale, system, context, and time.

Run `paperci explain PCI-MECH-001` for the initial machine-readable rule explanation.
Passing that core gate means only that the claim is not supported exclusively by
non-mechanistic evidence; it does not certify that the complete mechanism is proven.
