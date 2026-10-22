-- RECHECK-031/032: content-only, preserve IDs, position and correct index.
-- No new tables or changes to RLS/grants; no learner-data writes.
DO $recheck$
DECLARE actual jsonb;
BEGIN
    SELECT options INTO actual FROM public.questions WHERE lesson_id='housing-quiz' AND position=0 AND correct=1 AND is_active;
    IF actual IS NULL OR actual NOT IN ('["отопление","залог","счётчик"]'::jsonb, '["плата за отопление","сумма, внесённая как обеспечение при аренде","прибор для измерения расхода электричества"]'::jsonb) THEN
        RAISE EXCEPTION 'Unexpected deposit question content';
    END IF;
    UPDATE public.questions SET options='["плата за отопление","сумма, внесённая как обеспечение при аренде","прибор для измерения расхода электричества"]'::jsonb WHERE lesson_id='housing-quiz' AND position=0 AND correct=1;
    SELECT glossary->'zapraszam' INTO actual FROM public.reading_texts WHERE id='pierwszy-dzien-na-kursie' AND is_active;
    IF actual IS NULL OR actual NOT IN ('"прошу / проходите"'::jsonb, '{"lemma":"zapraszać","translation":"прошу / проходите","part_of_speech":"глагол"}'::jsonb) THEN
        RAISE EXCEPTION 'Unexpected zapraszam glossary entry';
    END IF;
    UPDATE public.reading_texts SET glossary=jsonb_set(glossary,'{zapraszam}','{"lemma":"zapraszać","translation":"прошу / проходите","part_of_speech":"глагол"}'::jsonb) WHERE id='pierwszy-dzien-na-kursie';
END $recheck$;
