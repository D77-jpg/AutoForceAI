"""Offline retrieval must ground natural questions without an embedding provider."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.rag.retriever import KnowledgeRetriever
from database.base import Base
from database.shared_models import KnowledgeBase, KnowledgeDoc, KnowledgeChunk


@pytest.fixture
def retriever(monkeypatch):
    for key in ('OPENAI_API_KEY', 'DASHSCOPE_API_KEY', 'ZHIPUAI_API_KEY'):
        monkeypatch.setenv(key, '')
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        library = KnowledgeBase(name='Synthetic facts')
        other_library = KnowledgeBase(name='Other scope')
        db.add_all([library, other_library])
        db.flush()
        for kb, content in (
            (library, 'Acceptance_widget MOQ is 73 units. Acceptance_widget lead time is 19 days.'),
            (library, '虚构产品最小起订量为73件，交期为19天。'),
            (other_library, 'Acceptance_widget MOQ is 999 units.'),
        ):
            doc = KnowledgeDoc(kb_id=kb.id, filename='facts.txt', status='indexed', chunk_count=1)
            db.add(doc)
            db.flush()
            db.add(KnowledgeChunk(doc_id=doc.id, chunk_index=0, chunk_text=content))
        db.commit()
        yield KnowledgeRetriever(db), library.id
    engine.dispose()


@pytest.mark.parametrize('question,expected', [
    ('What are the MOQ and lead time for Acceptance_widget? Cite the uploaded document.', '73 units'),
    ('What is the MOQ for Acceptance_widget?', '73 units'),
    ('虚构产品最小起订量和交期是多少？', '73件'),
])
def test_natural_question_retrieves_uploaded_facts_in_scope(retriever, question, expected):
    search, library_id = retriever
    hits = search.search_multi_kb([library_id], question)
    assert hits and any(expected in hit['content'] for hit in hits)
    assert all(hit['kb_id'] == library_id for hit in hits)
    assert not any('999' in hit['content'] for hit in hits)


@pytest.mark.parametrize('question', ['What are the details?', 'unrelated aircraft specifications'])
def test_common_words_or_unrelated_questions_do_not_create_sources(retriever, question):
    search, library_id = retriever
    assert search.search_multi_kb([library_id], question) == []
