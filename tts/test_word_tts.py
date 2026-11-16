import unittest
from word_tts import align_words,sentences
class WordTimingTests(unittest.TestCase):
 def test_korean_whitespace_words(self):
  raw=[{'text':s,'offset':i*10000000,'duration':5000000} for i,s in enumerate(['나는','맛있는','밥이','먹고싶다'])]
  result=align_words('나는 맛있는 밥이 먹고싶다.',raw)
  self.assertEqual([w['text'] for w in result],['나는','맛있는','밥이','먹고싶다'])
  self.assertEqual([w['start'] for w in result],[0,1,2,3])
 def test_subword_boundaries_join_into_spaced_word(self):
  raw=[{'text':'먹고','offset':0,'duration':5000000},{'text':'싶다','offset':5000000,'duration':5000000}]
  self.assertEqual(align_words('먹고싶다.',raw),[{'text':'먹고싶다','start':0,'end':1}])
 def test_refuse_invented_alignment(self):
  with self.assertRaises(ValueError):align_words('나는 밥이', [{'text':'나는밥이','offset':0,'duration':10000000}])
  with self.assertRaises(ValueError):align_words('3개', [{'text':'세개','offset':0,'duration':10000000}])
 def test_sentences_clear_at_punctuation_and_newline(self):
  self.assertEqual(sentences('첫 문장입니다. 둘째 문장입니다!\n마지막 문장'),['첫 문장입니다.','둘째 문장입니다!','마지막 문장'])
if __name__=='__main__':unittest.main()
