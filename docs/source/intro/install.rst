.. _intro-install:

==================
安装指南
==================


准备Ubuntu
""""""""""""""""""

建议使用一个新安装干净的Ubuntu环境，作者使用环境如下：

*   Memory: 16 GiB
*   Processor: Intel® Core™ i7-4790K CPU @ 4.00GHz × 8
*   Graphics: Intel® Haswell Desktop
*   OS type: 64-bit
*   Disk: 2 TB


安装Anaconda
""""""""""""""""""

在Continuum官网下载Python 2.7版本Linux 64-Bit的Anaconda，我这里下载完成后的文件名为Anaconda2-4.0.0-Linux-x86_64.sh。

打开Terminal（终端），进入文件所在的目录，输入如下命令:

..  code-block:: bash

    bash Anaconda2-4.0.0-Linux-x86_64.sh

设置方面除了最后一个选择可以一路回车，到最后一项设置是否要将Anaconda添加到bash的PATH中时，注意选yes。


安装其他依赖
""""""""""""""""""

使用pip安装MongoDB驱动和Qt黑色主题，注意不要加sudo:

..  code-block:: bash

    pip install pymongo qdarkstyle


使用apt-get安装编译API相关的工具：

..  code-block:: bash

    sudo apt-get install git build-essential libboost-all-dev python-dev cmake


运行InplusTrader
""""""""""""""""""

使用git从Github上下载InplusTrader框架:

..  code-block:: bash

    git clone http://github.com/zhengwsh/InplusTrader_Linux.git
