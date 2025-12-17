#############################################################################
# test_dict_utils.py
#
# Comprehensive tests for DictUtils class.
#
# Test Coverage:
# - build_params: Basic filtering, flags, custom filter functions
# - filter_none: Convenience method for None-only filtering
# - filter_falsy: Convenience method for falsy filtering
# - Edge cases: Empty inputs, type errors, etc.
#
#############################################################################

import pytest
from typing import Any, Dict

from asdrp.util.dict_utils import DictUtils


class TestDictUtilsBuildParams:
    """Test DictUtils.build_params method."""
    
    def test_basic_filtering_excludes_none(self):
        """Test that None values are excluded by default."""
        result = DictUtils.build_params(a=1, b=None, c=2)
        assert result == {'a': 1, 'c': 2}
        assert 'b' not in result
    
    def test_basic_filtering_excludes_empty_string(self):
        """Test that empty strings are excluded by default."""
        result = DictUtils.build_params(a='value', b='', c='test')
        assert result == {'a': 'value', 'c': 'test'}
        assert 'b' not in result
    
    def test_basic_filtering_excludes_zero(self):
        """Test that zero is excluded by default."""
        result = DictUtils.build_params(a=1, b=0, c=2)
        assert result == {'a': 1, 'c': 2}
        assert 'b' not in result
    
    def test_basic_filtering_excludes_false(self):
        """Test that False is excluded by default."""
        result = DictUtils.build_params(a=True, b=False, c=1)
        assert result == {'a': True, 'c': 1}
        assert 'b' not in result
    
    def test_basic_filtering_includes_truthy_values(self):
        """Test that truthy values are included."""
        result = DictUtils.build_params(
            string='test',
            number=42,
            boolean=True,
            list=[1, 2, 3],
            dict={'key': 'value'}
        )
        assert result == {
            'string': 'test',
            'number': 42,
            'boolean': True,
            'list': [1, 2, 3],
            'dict': {'key': 'value'}
        }
    
    def test_include_zero_flag(self):
        """Test include_zero flag includes zero values."""
        result = DictUtils.build_params(a=1, b=0, c=2, include_zero=True)
        assert result == {'a': 1, 'b': 0, 'c': 2}
    
    def test_include_false_flag(self):
        """Test include_false flag includes False values."""
        result = DictUtils.build_params(a=True, b=False, c=1, include_false=True)
        assert result == {'a': True, 'b': False, 'c': 1}
    
    def test_include_empty_string_flag(self):
        """Test include_empty_string flag includes empty strings."""
        result = DictUtils.build_params(a='value', b='', c='test', include_empty_string=True)
        assert result == {'a': 'value', 'b': '', 'c': 'test'}
    
    def test_multiple_flags_combined(self):
        """Test that multiple flags can be combined."""
        result = DictUtils.build_params(
            a=1,
            b=0,
            c=False,
            d='',
            e=None,
            include_zero=True,
            include_false=True,
            include_empty_string=True
        )
        assert result == {'a': 1, 'b': 0, 'c': False, 'd': ''}
        assert 'e' not in result  # None is always excluded
    
    def test_custom_filter_func(self):
        """Test custom filter function."""
        def not_none(value: Any) -> bool:
            return value is not None
        
        result = DictUtils.build_params(
            a=1,
            b=None,
            c=0,
            d=False,
            e='',
            filter_func=not_none
        )
        assert result == {'a': 1, 'c': 0, 'd': False, 'e': ''}
    
    def test_custom_filter_func_overrides_flags(self):
        """Test that custom filter_func overrides default flags."""
        def only_strings(value: Any) -> bool:
            return isinstance(value, str)
        
        result = DictUtils.build_params(
            a='test',
            b=1,
            c=None,
            d='',
            include_zero=True,
            include_false=True,
            filter_func=only_strings
        )
        assert result == {'a': 'test', 'd': ''}
    
    def test_custom_filter_func_type_error(self):
        """Test that non-callable filter_func raises TypeError."""
        with pytest.raises(TypeError, match="filter_func must be callable"):
            DictUtils.build_params(a=1, filter_func="not a function")
    
    def test_empty_input(self):
        """Test that empty input returns empty dict."""
        result = DictUtils.build_params()
        assert result == {}
    
    def test_all_none_values(self):
        """Test that all None values result in empty dict."""
        result = DictUtils.build_params(a=None, b=None, c=None)
        assert result == {}
    
    def test_all_falsy_values(self):
        """Test that all falsy values result in empty dict."""
        result = DictUtils.build_params(
            none=None,
            zero=0,
            false=False,
            empty='',
            empty_list=[],
            empty_dict={}
        )
        assert result == {}
    
    def test_preserves_key_order(self):
        """Test that key order is preserved (Python 3.7+)."""
        result = DictUtils.build_params(
            first=1,
            second=2,
            third=3,
            fourth=None,
            fifth=5
        )
        keys = list(result.keys())
        assert keys == ['first', 'second', 'third', 'fifth']
    
    def test_real_world_api_params(self):
        """Test realistic API parameter building scenario."""
        params = DictUtils.build_params(
            location=(37.7749, -122.4194),
            radius=1000,
            keyword='restaurant',
            type=None,  # Optional parameter, should be filtered out
            language='en',
            max_results=10
        )
        assert params == {
            'location': (37.7749, -122.4194),
            'radius': 1000,
            'keyword': 'restaurant',
            'language': 'en',
            'max_results': 10
        }
        assert 'type' not in params
    
    def test_nested_structures(self):
        """Test that nested structures are preserved."""
        nested_dict = {'key': 'value', 'nested': {'deep': 'value'}}
        nested_list = [1, 2, [3, 4]]
        
        result = DictUtils.build_params(
            dict_param=nested_dict,
            list_param=nested_list,
            none_param=None
        )
        assert result['dict_param'] == nested_dict
        assert result['list_param'] == nested_list
        assert 'none_param' not in result


class TestDictUtilsFilterNone:
    """Test DictUtils.filter_none convenience method."""
    
    def test_filters_only_none(self):
        """Test that only None values are filtered."""
        result = DictUtils.filter_none(
            a=1,
            b=None,
            c=0,
            d=False,
            e='',
            f=[]
        )
        assert result == {'a': 1, 'c': 0, 'd': False, 'e': '', 'f': []}
        assert 'b' not in result
    
    def test_includes_all_non_none_values(self):
        """Test that all non-None values are included."""
        result = DictUtils.filter_none(
            string='test',
            number=0,
            boolean=False,
            empty_string='',
            empty_list=[],
            empty_dict={},
            none_value=None
        )
        assert len(result) == 6
        assert 'none_value' not in result
    
    def test_empty_input(self):
        """Test that empty input returns empty dict."""
        result = DictUtils.filter_none()
        assert result == {}
    
    def test_all_none(self):
        """Test that all None values result in empty dict."""
        result = DictUtils.filter_none(a=None, b=None, c=None)
        assert result == {}


class TestDictUtilsFilterFalsy:
    """Test DictUtils.filter_falsy convenience method."""
    
    def test_filters_all_falsy_values(self):
        """Test that all falsy values are filtered."""
        result = DictUtils.filter_falsy(
            a=1,
            b=None,
            c=0,
            d=False,
            e='',
            f=[],
            g={}
        )
        assert result == {'a': 1}
    
    def test_includes_only_truthy_values(self):
        """Test that only truthy values are included."""
        result = DictUtils.filter_falsy(
            string='test',
            number=42,
            boolean=True,
            list=[1, 2],
            dict={'key': 'value'},
            none=None,
            zero=0,
            false=False,
            empty=''
        )
        assert result == {
            'string': 'test',
            'number': 42,
            'boolean': True,
            'list': [1, 2],
            'dict': {'key': 'value'}
        }
    
    def test_empty_input(self):
        """Test that empty input returns empty dict."""
        result = DictUtils.filter_falsy()
        assert result == {}
    
    def test_all_falsy(self):
        """Test that all falsy values result in empty dict."""
        result = DictUtils.filter_falsy(
            none=None,
            zero=0,
            false=False,
            empty='',
            empty_list=[],
            empty_dict={}
        )
        assert result == {}


class TestDictUtilsEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_float(self):
        """Test that zero float is handled correctly."""
        result = DictUtils.build_params(a=0.0, b=1.0, include_zero=True)
        assert result == {'a': 0.0, 'b': 1.0}
    
    def test_negative_zero(self):
        """Test that negative zero is handled correctly."""
        result = DictUtils.build_params(a=-0.0, b=1, include_zero=True)
        assert result == {'a': -0.0, 'b': 1}
    
    def test_nan_value(self):
        """Test that NaN values are handled."""
        import math
        result = DictUtils.build_params(a=math.nan, b=1)
        # NaN is truthy in Python
        assert 'a' in result
        assert math.isnan(result['a'])
        assert result['b'] == 1
    
    def test_infinity_value(self):
        """Test that infinity values are handled."""
        import math
        result = DictUtils.build_params(a=math.inf, b=-math.inf, c=1)
        assert result == {'a': math.inf, 'b': -math.inf, 'c': 1}
    
    def test_zero_length_string_vs_empty_string(self):
        """Test that zero-length string equals empty string."""
        empty1 = ''
        empty2 = str()
        result = DictUtils.build_params(a=empty1, b=empty2, include_empty_string=True)
        assert result == {'a': '', 'b': ''}
    
    def test_whitespace_string(self):
        """Test that whitespace-only strings are included (they're truthy)."""
        result = DictUtils.build_params(a='   ', b='\t\n', c='')
        assert result == {'a': '   ', 'b': '\t\n'}
        assert 'c' not in result
    
    def test_complex_types(self):
        """Test that complex types are handled correctly."""
        class CustomClass:
            def __bool__(self):
                return True
        
        custom = CustomClass()
        result = DictUtils.build_params(a=custom, b=None)
        assert 'a' in result
        assert isinstance(result['a'], CustomClass)
        assert 'b' not in result

