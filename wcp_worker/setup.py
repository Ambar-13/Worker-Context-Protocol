from setuptools import find_packages, setup

PACKAGE_NAME = "wcp_worker"

setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
         [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml"]),
        (f"share/{PACKAGE_NAME}/launch", ["launch/wcp_worker.launch.py"]),
        (f"share/{PACKAGE_NAME}/config", ["config/wcp_worker.yaml"]),
    ],
    install_requires=["setuptools", "websockets>=11", "cryptography>=42"],
    zip_safe=True,
    maintainer="Rentably Pte Ltd",
    maintainer_email="dev@rentably.ai",
    description="WCP v0.1 reference ROS 2 plugin",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "wcp_worker = wcp_worker.plugin:main",
        ],
    },
)
