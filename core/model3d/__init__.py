"""Generatori parametrici — SPEC §17.1-17.3, ADR-014.

La geometria vive **qui**, non nel renderer: l'invariante 1 dice che le
operazioni reali sono del core, e un file su disco e' un'operazione reale. Il
renderer riceve `model3d.preview` e MOSTRA — il componente che lo incassa
estende `ParametricComponent` senza generare niente e passa `qualityGate()`
prima del render.

Nessun modulo di questo package importa `trimesh`: qui si producono vertici,
triangoli e linee di costruzione in numpy. Chi scrive il file e'
`core/tools/model3d.py`, e chi lo rilegge per verificarlo e' `glb_lettore`,
che usa la sola libreria standard.
"""
