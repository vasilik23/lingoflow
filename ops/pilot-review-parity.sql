-- Read-only projection for the three editorial pilots; no learner tables.
-- Contains answer keys. Keep results in the private review packet, not CI artifacts.
select jsonb_agg(jsonb_build_object(
'id',t.id,'level',c.level,'title',t.title,
'lessons',(select jsonb_agg(jsonb_build_object(
'id',l.id,'kind',l.kind,'title',l.title,'description',l.description,'theory_title',l.theory_title,'theory_sections',l.theory_sections,'source_metadata',l.source_metadata,
'questions',coalesce((select jsonb_agg(jsonb_build_object('ref',l.id||':q:'||q.position,'prompt',q.prompt,'options',q.options,'correct',q.correct,'explanation',q.explanation) order by q.position,q.id) from public.questions q where q.lesson_id=l.id and q.is_active),'[]'::jsonb),
'cards',coalesce((select jsonb_agg(jsonb_build_object('id',f.id,'polish',f.polish,'translation',f.translation,'example',f.example,'source_metadata',f.source_metadata) order by lf.position,lf.flashcard_id) from public.lesson_flashcards lf join public.flashcards f on f.id=lf.flashcard_id where lf.lesson_id=l.id and f.is_active),'[]'::jsonb)
) order by l.id) from public.lessons l where l.topic_id=t.id and l.is_active and l.id in ('words','grammar','review','a1read-kurs-check','quiz','housing-words','housing-grammar','housing-review','housing-reading-check','housing-quiz','bio-words','bio-grammar','bio-review','bio-reading-check','bio-quiz')),
'reading',(select jsonb_build_object('id',r.id,'title',r.title,'paragraphs',r.paragraphs,'source_glossary',r.glossary,'source_metadata',r.source_metadata) from public.reading_texts r where r.topic_id=t.id and r.is_active and r.level=c.level and r.id in ('pierwszy-dzien-na-kursie','usterka-w-mieszkaniu','bio-droga-joanny'))
) order by t.id) as topics from public.topics t join public.courses c on c.id=t.course_id where t.id in ('introductions','housing-services','b1-biography') and t.is_active and c.is_active;
