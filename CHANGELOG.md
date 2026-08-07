# Changelog

## [2.0.0](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.3.6...v2.0.0) (2026-08-07)


### ⚠ BREAKING CHANGES

* Python 3.11, 3.12 and 3.13 are no longer supported. Consumers on those interpreters must stay on 1.3.6.

### Build System

* require Python 3.14 ([3632046](https://github.com/roquerodrigo/midea-dishwasher-api/commit/3632046da81b27419b6de67fe65848428ba1b784))

## [1.3.6](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.3.5...v1.3.6) (2026-08-07)


### Bug Fixes

* **scripts:** repair the state dump import and share the .env loader ([c5c1921](https://github.com/roquerodrigo/midea-dishwasher-api/commit/c5c1921e8d768e1baadeecef624f711406573074))
* **transport:** wrap socket errors in V3Error ([3b65413](https://github.com/roquerodrigo/midea-dishwasher-api/commit/3b65413028fcfee50db59898ebbfdf81778a95fa))


### Code Refactoring

* give the two header length constants distinct names ([43e4bf2](https://github.com/roquerodrigo/midea-dishwasher-api/commit/43e4bf2501577da236f0809ed7d5b32a116aa2d5))
* **security:** derive the session key with a length-strict zip ([c825f6a](https://github.com/roquerodrigo/midea-dishwasher-api/commit/c825f6a60ed3f978d351412b6a0183b4f37f1c6d))


### Dependencies

* **deps:** bump the python-deps group across 1 directory with 2 updates ([53dfb8e](https://github.com/roquerodrigo/midea-dishwasher-api/commit/53dfb8ee894d646acf44911ac5624659daecd1e7))


### Documentation

* describe the real release and testing setup ([755c2cc](https://github.com/roquerodrigo/midea-dishwasher-api/commit/755c2ccd051ee5b3421acae76cc21b929a0b42d1))
* record the lint, typing and interpreter-support policy ([1d52d11](https://github.com/roquerodrigo/midea-dishwasher-api/commit/1d52d116ae298bd33a5f87bdc45f00d1e41429d0))


### Continuous Integration

* analyse pull requests opened against any branch ([8f756c5](https://github.com/roquerodrigo/midea-dishwasher-api/commit/8f756c508c94ec685a35095cb248a8ba7c5c3472))
* run the suite on the oldest supported interpreter ([72ae87c](https://github.com/roquerodrigo/midea-dishwasher-api/commit/72ae87c80ac8aa32f5f6615d912a9297a20da288))


### Miscellaneous Chores

* declare the Python floor the source actually requires ([ab5abb4](https://github.com/roquerodrigo/midea-dishwasher-api/commit/ab5abb466cb6de5bd51a79cecb225b713d9a0f68))
* move CI to the shared workflows repository ([e0a8b14](https://github.com/roquerodrigo/midea-dishwasher-api/commit/e0a8b14b6dd23631e1797c1026ea2fdfc2af042b))
* release on every conventional commit type ([103898a](https://github.com/roquerodrigo/midea-dishwasher-api/commit/103898a8b634e8678a365d15d34c20885ee1de6d))
* translate the PyPI description and test docstrings to English ([f13638e](https://github.com/roquerodrigo/midea-dishwasher-api/commit/f13638e50276c44d4e37c0332c27e6744410cc05))
* untrack IDE settings and run lint hooks through uv ([f0a9ed9](https://github.com/roquerodrigo/midea-dishwasher-api/commit/f0a9ed96708c2218a8b4d539ca0b10f72e13d0ab))

## [1.3.5](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.3.4...v1.3.5) (2026-08-03)


### Documentation

* track the agent guide and record the lint gotchas ([441441e](https://github.com/roquerodrigo/midea-dishwasher-api/commit/441441e114c3bfd0068f4c0b9de377e9a182f682))

## [1.3.4](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.3.3...v1.3.4) (2026-07-13)


### Bug Fixes

* relax cryptography pin to a range for HA compatibility ([58ee86e](https://github.com/roquerodrigo/midea-dishwasher-api/commit/58ee86eae193d2ac06e2bcb42eced49f928c0890))
* relax cryptography pin to a range for Home Assistant compatibility ([756463f](https://github.com/roquerodrigo/midea-dishwasher-api/commit/756463f527392a3b3c4012857fd8a11141e623bd))

## [1.3.3](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.3.2...v1.3.3) (2026-06-21)


### Documentation

* fix stale CODE_STYLE.md references ([043dafb](https://github.com/roquerodrigo/midea-dishwasher-api/commit/043dafbe6e5933c15f6727a0986b98e7e1e2c06f))
* fix stale CODE_STYLE.md references ([cf17b5c](https://github.com/roquerodrigo/midea-dishwasher-api/commit/cf17b5c1b42fb320954a5c33627ff9ad8264ce0c))

## [1.3.2](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.3.1...v1.3.2) (2026-05-25)


### Documentation

* add CI and PyPI badges ([48ea5ad](https://github.com/roquerodrigo/midea-dishwasher-api/commit/48ea5ad4d806522649c3bcd19aee6ffefbfce47c))
* add CI and PyPI badges ([e1764c3](https://github.com/roquerodrigo/midea-dishwasher-api/commit/e1764c3e0fed2aa67febe0f032f80bd68c25c09c))

## [1.3.1](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.3.0...v1.3.1) (2026-05-22)


### Documentation

* standardize CODE_STYLE.md template ([ccee432](https://github.com/roquerodrigo/midea-dishwasher-api/commit/ccee432802c589f704554012cca926e293f5873b))
* standardize CODE_STYLE.md template ([f2ea70e](https://github.com/roquerodrigo/midea-dishwasher-api/commit/f2ea70e86216e31ddcc9e415a12bde65861e6027))

## [1.3.0](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.2.0...v1.3.0) (2026-05-09)


### Features

* **state:** expose extra_drying flag in DishwasherStatus ([a59cca3](https://github.com/roquerodrigo/midea-dishwasher-api/commit/a59cca3722e0c9403893a87455e9a2fb20a76ddf))

## [1.2.0](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.1.0...v1.2.0) (2026-05-09)


### Features

* **state:** expose currently selected program (mode) in DishwasherStatus ([2368e16](https://github.com/roquerodrigo/midea-dishwasher-api/commit/2368e1623f48cfd5d3833d6210f4b5a3d7ba477f))

## [1.1.0](https://github.com/roquerodrigo/midea-dishwasher-api/compare/v1.0.1...v1.1.0) (2026-05-09)


### Features

* **state:** expose current rinse-aid level (bright) in DishwasherStatus ([3a0958c](https://github.com/roquerodrigo/midea-dishwasher-api/commit/3a0958caf535a3ea3d87864c4fcad8555968e0f2))


### Dependencies

* refresh uv.lock ([fd72c88](https://github.com/roquerodrigo/midea-dishwasher-api/commit/fd72c88f401668e6f2ef8547124cdabed4f56d5a))
