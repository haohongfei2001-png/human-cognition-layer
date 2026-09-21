"""Integration against the actual pinned SOTOPIA module; network is mocked."""
import importlib
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import BaseModel
from sotopia.generation_utils.output_parsers import PydanticOutputParser, StrOutputParser

module = importlib.import_module('sotopia.generation_utils.generate')
MODEL = 'custom/deepseek-flash@https://api.deepseek.com'
NORMALIZED = 'openai/deepseek-flash'
KEY = 'synthetic-test-key'

def response(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

class Value(BaseModel):
    value: int

class Routing(unittest.IsolatedAsyncioTestCase):
    async def test_plain_helper_preserves_custom_identity(self):
        with patch.object(module, 'acompletion', AsyncMock(return_value=response('fixed'))) as call:
            result = await module.format_bad_output('bad', StrOutputParser(), NORMALIZED, base_url='https://api.deepseek.com', api_key=KEY)
            self.assertEqual(result, 'fixed')
            self.assertEqual(call.await_args.kwargs['base_url'], 'https://api.deepseek.com')
            self.assertEqual(call.await_args.kwargs['api_key'], KEY)
            self.assertEqual(call.await_args.kwargs['model'], NORMALIZED)

    async def test_real_generation_parse_failure_repairs_once_with_same_provider(self):
        parser = PydanticOutputParser(pydantic_object=Value)
        with patch.dict(os.environ, {'CUSTOM_API_KEY': KEY}), patch.object(module, 'acompletion', AsyncMock(side_effect=[response('invalid'),response('{"value":7}')])) as call:
            value = await module.agenerate(model_name=MODEL, template='{prompt}', input_values={'prompt':'synthetic'}, output_parser=parser, bad_output_process_model=NORMALIZED)
            self.assertEqual(value.value, 7)
            self.assertEqual(call.await_count, 2)
            for item in call.await_args_list:
                self.assertEqual(item.kwargs['base_url'], 'https://api.deepseek.com')
                self.assertEqual(item.kwargs['api_key'], KEY)
                self.assertEqual(item.kwargs['model'], NORMALIZED)
            self.assertIn('response_format', call.await_args.kwargs)

    async def test_invalid_repair_does_not_add_retries(self):
        with patch.dict(os.environ, {'CUSTOM_API_KEY': KEY}), patch.object(module, 'acompletion', AsyncMock(return_value=response('invalid'))) as call:
            with self.assertRaises(Exception):
                await module.agenerate(model_name=MODEL, template='{prompt}', input_values={'prompt':'synthetic'}, output_parser=PydanticOutputParser(pydantic_object=Value), bad_output_process_model=NORMALIZED)
            self.assertEqual(call.await_count, 2)

    async def test_alternate_model_or_provider_cannot_receive_custom_credentials(self):
        for alternate in [None,'gpt-5-mini-2025-08-07','openai/another-model','custom/deepseek-flash@https://unrelated.invalid']:
            with self.subTest(alternate=alternate), patch.dict(os.environ, {'CUSTOM_API_KEY': KEY}), patch.object(module, 'acompletion', AsyncMock(return_value=response('invalid'))) as call:
                with self.assertRaisesRegex(ValueError, 'original model/provider'):
                    await module.agenerate(model_name=MODEL, template='{prompt}', input_values={'prompt':'synthetic'}, output_parser=PydanticOutputParser(pydantic_object=Value), bad_output_process_model=alternate)
                self.assertEqual(call.await_count, 1)

    async def test_native_helper_keeps_native_credential_resolution(self):
        with patch.object(module, 'acompletion', AsyncMock(return_value=response('ok'))) as call:
            await module.format_bad_output('bad', StrOutputParser(), 'openai/synthetic')
            self.assertIsNone(call.await_args.kwargs['api_key'])
            self.assertIsNone(call.await_args.kwargs['base_url'])

    async def test_evaluator_explicitly_selects_original_model(self):
        evaluator=importlib.import_module('scripts.run_sotopia_hard_one_ab')
        fake=SimpleNamespace(evaluations={})
        with patch.object(evaluator,'agenerate',AsyncMock(return_value=fake)) as call:
            await evaluator.evaluate_transcript([('Alice',SimpleNamespace(to_natural_language=lambda:'synthetic statement'))])
            self.assertEqual(call.await_args.kwargs['model_name'],MODEL)
            self.assertEqual(call.await_args.kwargs['bad_output_process_model'],NORMALIZED)

if __name__ == '__main__':
    unittest.main()
