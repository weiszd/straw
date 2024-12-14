from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys
import setuptools
import os
import warnings
from distutils import log
log.set_verbosity(0)

__version__ = '1.3.2'

# Force warnings to always be shown
warnings.filterwarnings('always', category=UserWarning)

def emit_warning(message):
    """Emit a warning that will always be shown"""
    # Write directly to stdout and flush
    # sys.stdout.write(f"\n{message}\n")
    # sys.stdout.flush()
    # Also emit as warning
    warnings.warn(message, category=UserWarning, stacklevel=1, source=None )

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


class GetPybindInclude(object):
    """Helper class to determine the pybind11 include path

    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)


ext_modules = [
    Extension(
        'hicstraw',
        ['src/straw.cpp'],
        include_dirs=[
            # Path to pybind11 headers
            GetPybindInclude(),
            GetPybindInclude(user=True)
        ],
        language='c++'
    ),
]


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
        f.write('int main (int argc, char **argv) { return 0; }')
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14/17] compiler flag.

    The newer version is prefered over c++11 (when it is available).
    """
    flags = ['-std=c++14', '-std=c++11']

    for flag in flags:
        if has_flag(compiler, flag): return flag

    raise RuntimeError('Unsupported compiler -- at least C++11 support '
                       'is needed!')


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""
    c_opts = {
        'msvc': ['/EHsc'],
        'unix': [],
    }
    l_opts = {
        'msvc': [],
        'unix': [],
    }

        
    if sys.platform == 'darwin':
        darwin_opts = ['-stdlib=libc++', '-mmacosx-version-min=10.7']
        c_opts['unix'] += darwin_opts
        l_opts['unix'] += darwin_opts

    def build_extensions(self):
        try:
            emit_warning("hic-straw: Attempting to build from source...")
            self._build_extensions_regular()
            emit_warning("hic-straw: Successfully built from source")
        except Exception as e:
            message = """hic-straw: Build from source failed!
Missing required packages:
  - libcurl4-openssl-dev (curl development package)
  - zlib1g-dev (zlib development package)

Install commands:
  Ubuntu/Debian: sudo apt-get install libcurl4-openssl-dev zlib1g-dev
  RHEL/CentOS:  sudo yum install libcurl-devel zlib-devel
  macOS:        brew install curl zlib

Trying pre-built binary..."""


            emit_warning(message)
            
            # Ask user for permission to use pre-built binary
            try:
                response = input("\nhic-straw: Would you like to use a pre-built binary instead? [Y/n] ").lower()
                if response in ('n', 'no'):
                    emit_warning("hic-straw: User chose not to use pre-built binary")
                    raise Exception("User chose not to use pre-built binary")
            except (EOFError, KeyboardInterrupt):
                # Handle non-interactive environments
                emit_warning("hic-straw: Non-interactive environment detected, defaulting to Yes")
                
            try:
                self._use_prebuilt_binary()
                emit_warning("hic-straw: Successfully installed using pre-built binary")
                emit_warning("hic-straw: Note: Using pre-built binary because build from source failed")
            except Exception as prebuilt_error:
                error_message = """hic-straw ERROR: No pre-built binary available!
Please install the required development packages listed above and try again."""
                emit_warning(error_message)
                raise

    def _build_extensions_regular(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])
        link_opts = self.l_opts.get(ct, [])
        if ct == 'unix':
            # Try static linking first
            try:
                import tempfile
                import os
                
                # Create a test source file
                with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
                    f.write('#include <curl/curl.h>\n#include <zlib.h>\nint main() { return 0; }')
                    f.flush()
                    
                    try:
                        objects = self.compiler.compile([f.name], 
                                                      extra_preargs=['-DCURL_STATICLIB', '-DZ_STATICLIB'])
                        self.compiler.link_executable(objects, 'test',
                                                    libraries=['curl', 'z'],
                                                    library_dirs=['/usr/lib'])
                        link_opts = ['-DCURL_STATICLIB', '-DZ_STATICLIB', '-lcurl', '-lz']
                    except Exception as e:
                        emit_warning(f"Static linking failed: {str(e)}")
                        # Fall back to dynamic linking
                        try:
                            objects = self.compiler.compile([f.name])
                            self.compiler.link_executable(objects, 'test',
                                                        libraries=['curl', 'z'],
                                                        library_dirs=['/usr/lib'])
                            link_opts = ['-lcurl', '-lz']
                        except Exception as e:
                            emit_warning(f"Dynamic linking failed: {str(e)}")
                            raise Exception("Failed to link with libcurl and libz")
            except Exception as e:
                emit_warning(f"Compilation test failed: {str(e)}")
                raise Exception("Failed to link with libcurl and libz")
            finally:
                # Clean up test executable if it exists
                if os.path.exists('test'):
                    os.remove('test')
                # Clean up any object files
                for obj in os.listdir('.'):
                    if obj.endswith('.o'):
                        os.remove(obj)
                
            opts.append('-DVERSION_INFO="%s"' % self.distribution.get_version())
            opts.append(cpp_flag(self.compiler))
            if has_flag(self.compiler, '-fvisibility=hidden'):
                opts.append('-fvisibility=hidden')
        elif ct == 'msvc':
            opts.append('/DVERSION_INFO=\\"%s\\"' % self.distribution.get_version())
        for ext in self.extensions:
            ext.extra_compile_args = opts
            ext.extra_link_args = link_opts
        build_ext.build_extensions(self)

    def _use_prebuilt_binary(self):
        """Try to use pre-built binary for current platform"""
        import platform
        import shutil
        import os

        # Determine platform-specific binary path
        system = platform.system().lower()
        machine = platform.machine().lower()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        # Construct path to pre-built binary
        binary_name = f"hicstraw.{system}.{machine}.cp{python_version}-{python_version}.so"
        prebuilt_path = os.path.join('prebuilt', binary_name)
        
        if not os.path.exists(prebuilt_path):
            raise Exception(
                f"Compilation failed and no pre-built binary found for your platform "
                f"({system} {machine} Python {python_version})"
            )
        
        # Create the build directory if it doesn't exist
        build_lib = self.build_lib
        os.makedirs(build_lib, exist_ok=True)
        
        # Copy pre-built binary directly to build directory, not in a package subdirectory
        shutil.copy2(prebuilt_path, os.path.join(build_lib, os.path.basename(prebuilt_path)))
        emit_warning(f"Using pre-built binary: {prebuilt_path}")


setup(
    name='hic-straw',
    version=__version__,
    author='Neva C. Durand, Muhammad S Shamim',
    author_email='neva@broadinstitute.org',
    license='MIT',
    keywords=['Hi-C', '3D Genomics', 'Chromatin', 'ML'],
    url='https://github.com/aidenlab/straw',
    description='Straw bound with pybind11',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    ext_modules=ext_modules,
    install_requires=['pybind11>=2.4'],
    setup_requires=['pybind11>=2.4'],
    python_requires='>3.3',
    cmdclass={'build_ext': BuildExt},
    zip_safe=False,
)
