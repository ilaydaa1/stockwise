# Synthetic dataset

**Everything in this folder is artificial.** The files were produced by a simulation of a fictional shop. They do not describe any real business, person, supplier or transaction.

- What the files contain and how they relate: [docs/dataset.md](../../docs/dataset.md)
- How costs are calculated: [docs/costing.md](../../docs/costing.md)
- Seed, period, row counts and scripted scenarios: [manifest.json](manifest.json)

The `ground_truth` folder holds numbers that only exist because the data is simulated, such as demand lost to stockouts. Use it to check an analysis, not as input to one.

Do not edit these files by hand. To change them, change the generator's configuration and regenerate from the `backend` folder:

```bash
python -m stockwise.datagen generate --reset
```
