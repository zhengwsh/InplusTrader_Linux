
====================================
InplusTrader |version| Documentation
====================================

..  image:: https://img.shields.io/travis/ricequant/rqalpha/master.svg
    :target: https://travis-ci.org/ricequant/rqalpha/branches
    :alt: Build

..  image:: https://coveralls.io/repos/github/ricequant/rqalpha/badge.svg?branch=master
    :target: https://coveralls.io/github/ricequant/rqalpha?branch=master

..  image:: https://readthedocs.org/projects/rqalpha/badge/?version=stable
    :target: http://rqalpha.readthedocs.io/zh_CN/stable/?badge=stable
    :alt: Documentation Status

..  image:: https://img.shields.io/pypi/v/rqalpha.svg
    :target: https://pypi.python.org/pypi/rqalpha
    :alt: PyPI Version

..  image:: https://img.shields.io/pypi/l/rqalpha.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: License

..  image:: https://img.shields.io/pypi/pyversions/rqalpha.svg
    :target: https://pypi.python.org/pypi/rqalpha
    :alt: Python Version Support


InplusTrader 从数据获取、算法交易、回测引擎，实盘模拟，实盘交易到数据分析，为程序化交易者提供了全套解决方案。

InplusTrader 具有灵活的配置方式，强大的扩展性，用户可以非常容易地定制专属于自己的程序化交易系统。

.. note::
    结合深度学习和强化学习等最新技术，助力量化交易。


特点
============================

======================    =================================================================================
易于使用                    让您集中于策略的开发，一行简单的命令就可以执行您的策略。
完善的文档                   您可以直接访问 `InplusTrader 文档`_ 来获取您需要的信息。
稳定的环境                   策略和数据做到问题做到快速解决。
灵活的配置                   您可以使用多种方式来配置和运行策略，只需简单的配置就可以构建适合自己的交易系统。
强大的扩展性                 开发者可以基于我们提供的接口来进行扩展。
======================    =================================================================================


Feature Status
============================

*   深度学习 --> `tensorflow`_

    * ✅ 深度学习模块

获取帮助
============================

关于InplusTrader的任何问题可以通过以下途径来获取帮助

*  查看 `FAQ`_ 页面找寻常见问题及解答
*  在 `Github Issue`_ 中提交issue


.. _Github Issue: https://github.com/ricequant/rqalpha/issues
.. _Ricequant: https://www.ricequant.com/algorithms
.. _RQAlpha 文档: http://rqalpha.readthedocs.io/zh_CN/latest/
.. _Ricequant 文档: https://www.ricequant.com/api/python/chn
.. _Ricequant 社区: https://www.ricequant.com/community/category/all/
.. _FAQ: http://rqalpha.readthedocs.io/zh_CN/latest/faq.html
.. _索引: http://rqalpha.readthedocs.io/zh_CN/latest/genindex.html

.. _RQAlpha 介绍: http://rqalpha.readthedocs.io/zh_CN/latest/intro/overview.html
.. _安装指南: http://rqalpha.readthedocs.io/zh_CN/latest/intro/install.html
.. _10分钟学会 RQAlpha: http://rqalpha.readthedocs.io/zh_CN/latest/intro/tutorial.html
.. _策略示例: http://rqalpha.readthedocs.io/zh_CN/latest/intro/examples.html

.. _API: http://rqalpha.readthedocs.io/zh_CN/latest/api/base_api.html

.. _如何贡献代码: http://rqalpha.readthedocs.io/zh_CN/latest/development/make_contribute.html
.. _基本概念: http://rqalpha.readthedocs.io/zh_CN/latest/development/basic_concept.html
.. _RQAlpha 基于 Mod 进行扩展: http://rqalpha.readthedocs.io/zh_CN/latest/development/mod.html
.. _History: http://rqalpha.readthedocs.io/zh_CN/latest/history.html
.. _TODO: https://github.com/ricequant/rqalpha/blob/master/TODO.md
.. _develop 分支: https://github.com/ricequant/rqalpha/tree/develop
.. _master 分支: https://github.com/ricequant/rqalpha
.. _rqalpha_mod_sys_stock_realtime: https://github.com/ricequant/rqalpha/blob/master/rqalpha/mod/rqalpha_mod_sys_stock_realtime/README.rst
.. _rqalpha_mod_tushare: https://github.com/ricequant/rqalpha-mod-tushare
.. _通过 Mod 扩展 RQAlpha: http://rqalpha.io/zh_CN/latest/development/mod.html
.. _sys_analyser: https://github.com/ricequant/rqalpha/blob/master/rqalpha/mod/rqalpha_mod_sys_analyser/README.rst
.. _sys_funcat: https://github.com/ricequant/rqalpha/blob/master/rqalpha/mod/rqalpha_mod_sys_funcat/README.rst
.. _sys_progress: https://github.com/ricequant/rqalpha/blob/master/rqalpha/mod/rqalpha_mod_sys_progress/README.rst
.. _sys_risk: https://github.com/ricequant/rqalpha/blob/master/rqalpha/mod/rqalpha_mod_sys_risk/README.rst
.. _sys_simulation: https://github.com/ricequant/rqalpha/blob/master/rqalpha/mod/rqalpha_mod_sys_simulation/README.rst
.. _sys_stock_realtime: https://github.com/ricequant/rqalpha/blob/master/rqalpha/mod/rqalpha_mod_sys_stock_realtime/README.rst
.. _vnpy: https://github.com/ricequant/rqalpha-mod-vnpy
.. _sentry: https://github.com/ricequant/rqalpha-mod-sentry
.. _tushare: https://github.com/ricequant/rqalpha-mod-tushare
.. _shipane: https://github.com/wh1100717/rqalpha-mod-ShiPanE

.. toctree::
    :caption: 基础
    :hidden:

    intro/overview
    intro/install
    intro/tutorial
    intro/examples
    intro/detail_install
    intro/virtual_machine

.. toctree::
    :caption: API
    :hidden:

    api/base_api
    api/extend_api


.. toctree::
    :caption: 进阶
    :hidden:

    intro/run_algorithm
    intro/under_ide
    intro/optimizing_parameters


.. toctree::
    :caption: 开发
    :hidden:

    development/make_contribute
    development/basic_concept
    development/mod
    development/event_source
    development/data_source

.. toctree::
    :caption: 其他
    :hidden:

    history
