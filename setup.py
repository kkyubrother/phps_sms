from pathlib import Path
from setuptools import setup, find_packages

setup(
    name='phps_sms',
    version='0.4.0',
    url='https://github.com/kkyubrother/phps_sms',
    license=' Apache-2.0 License',
    author='Kkyubrother',
    author_email='kkyubrother@naver.com',
    description='Unified PHP School SMS, LMS and MMS module',
    long_description=Path(__file__).with_name('README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    packages=find_packages(include=['phps_sms', 'phps_sms.*', 'phps_sms_module', 'phps_sms_module.*']),
    py_modules=['kkyubr_sms'],
    python_requires='>=3.6',
    zip_safe=False,
    install_requires=['requests>=2.25.1', 'phpserialize>=1.3'],
)
