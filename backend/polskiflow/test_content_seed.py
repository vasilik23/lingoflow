from django.test import TestCase

from polskiflow.learning.models import (
    Course,
    Flashcard,
    Lesson,
    LessonFlashcard,
    Question,
    ReadingText,
    Topic,
)
from polskiflow.content import course_topics


class IntroductionsContentTests(TestCase):
    def test_introductions_topic_is_first(self):
        topic = Topic.objects.get(id="introductions")

        self.assertEqual(topic.position, 0)
        self.assertEqual(topic.title, "Знакомство")
        self.assertEqual(topic.course_id, "a1-foundations")

    def test_daily_plan_contains_complete_introductions_block(self):
        lessons = Lesson.objects.filter(topic_id="introductions")

        self.assertEqual(lessons.count(), 7)
        self.assertEqual(Question.objects.filter(lesson_id="grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="quiz").count(), 8)
        self.assertEqual(
            LessonFlashcard.objects.filter(lesson_id="words").count(), 8
        )
        self.assertEqual(
            LessonFlashcard.objects.filter(lesson_id="review").count(), 7
        )

    def test_original_content_has_source_metadata(self):
        expected_origin = "original"

        self.assertEqual(
            Lesson.objects.get(id="words").source_metadata["origin"],
            expected_origin,
        )
        self.assertEqual(
            Flashcard.objects.get(id="mam-na-imie").source_metadata["origin"],
            expected_origin,
        )
        self.assertEqual(
            ReadingText.objects.get(
                id="pierwszy-dzien-na-kursie"
            ).source_metadata["origin"],
            expected_origin,
        )

    def test_introductions_reading_has_glossary(self):
        reading = ReadingText.objects.get(id="pierwszy-dzien-na-kursie")

        self.assertEqual(reading.level, "A1")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertIn("przedstawia", reading.glossary)


class CountriesLanguagesContentTests(TestCase):
    def test_topic_follows_introductions(self):
        topic = Topic.objects.get(id="countries-languages")

        self.assertEqual(topic.position, 1)
        self.assertEqual(topic.course_id, "a1-foundations")

    def test_topic_has_complete_vertical_block(self):
        lessons = Lesson.objects.filter(topic_id="countries-languages")

        self.assertEqual(lessons.count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="countries-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="countries-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="countries-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="countries-review").count(), 7)

    def test_new_content_is_original_and_reading_has_glossary(self):
        reading = ReadingText.objects.get(id="rozmowa-w-miedzynarodowej-grupie")

        self.assertEqual(Lesson.objects.get(id="countries-words").source_metadata["origin"], "original")
        self.assertEqual(Flashcard.objects.get(id="pochodzic").source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertIn("międzynarodowa", reading.glossary)

    def test_course_catalog_groups_lessons_by_topic(self):
        topics = course_topics()

        self.assertEqual([topic["id"] for topic in topics[:2]], ["introductions", "countries-languages"])
        self.assertEqual(len(topics[0]["lessons"]), 7)
        self.assertEqual(len(topics[1]["lessons"]), 5)


class FamilyContentTests(TestCase):
    def test_family_topic_is_third(self):
        topic = Topic.objects.get(id="family")

        self.assertEqual(topic.position, 2)
        self.assertEqual(topic.course_id, "a1-foundations")

    def test_family_has_complete_vertical_block(self):
        self.assertEqual(Lesson.objects.filter(topic_id="family").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="family-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="family-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="family-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="family-review").count(), 7)

    def test_family_content_is_original_and_reading_has_glossary(self):
        reading = ReadingText.objects.get(id="niedziela-u-babci")

        self.assertEqual(Lesson.objects.get(id="family-words").source_metadata["origin"], "original")
        self.assertEqual(Flashcard.objects.get(id="rodzina").source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertIn("odwiedza", reading.glossary)

    def test_course_catalog_lists_family_after_first_topics(self):
        topics = course_topics()

        self.assertEqual([topic["id"] for topic in topics[:3]], ["introductions", "countries-languages", "family"])
        self.assertEqual(len(topics[2]["lessons"]), 5)


class DailyRoutineContentTests(TestCase):
    def test_daily_routine_is_fourth_complete_topic(self):
        topic = Topic.objects.get(id="daily-routine")

        self.assertEqual(topic.position, 3)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="daily-routine-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="daily-routine-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="daily-routine-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="daily-routine-review").count(), 7)

    def test_daily_reading_uses_lemma_aware_glossary(self):
        reading = ReadingText.objects.get(id="zwykly-dzien-oli")

        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["budzi"]["lemma"], "budzić się")
        self.assertEqual(reading.glossary["kanapkę"]["lemma"], "kanapka")

    def test_catalog_lists_first_four_curriculum_topics(self):
        topics = course_topics()

        self.assertEqual(
            [topic["id"] for topic in topics[:4]],
            ["introductions", "countries-languages", "family", "daily-routine"],
        )


class HomeContentTests(TestCase):
    def test_home_is_fifth_complete_topic(self):
        topic = Topic.objects.get(id="home")
        self.assertEqual(topic.position, 4)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="home-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="home-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="home-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="home-review").count(), 7)

    def test_home_reading_has_lemma_glossary(self):
        reading = ReadingText.objects.get(id="nowe-mieszkanie-marty")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["piętrze"]["lemma"], "piętro")
        self.assertEqual(reading.glossary["stoją"]["lemma"], "stać")

    def test_catalog_lists_home_after_daily_routine(self):
        self.assertEqual(
            [topic["id"] for topic in course_topics()[:5]],
            ["introductions", "countries-languages", "family", "daily-routine", "home"],
        )


class FoodShoppingContentTests(TestCase):
    def test_food_shopping_is_sixth_complete_topic(self):
        topic = Topic.objects.get(id="food-shopping")
        self.assertEqual(topic.position, 5)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="food-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="food-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="food-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="food-review").count(), 7)

    def test_food_reading_has_lemma_aware_glossary(self):
        reading = ReadingText.objects.get(id="zakupy-oli")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["idzie"]["lemma"], "iść")
        self.assertEqual(reading.glossary["torby"]["lemma"], "torba")

    def test_catalog_lists_first_six_curriculum_topics(self):
        self.assertEqual(
            [topic["id"] for topic in course_topics()[:6]],
            ["introductions", "countries-languages", "family", "daily-routine", "home", "food-shopping"],
        )


class CityDirectionsContentTests(TestCase):
    def test_city_directions_is_seventh_complete_topic(self):
        topic = Topic.objects.get(id="city-directions")
        self.assertEqual(topic.position, 6)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="city-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="city-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="city-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="city-review").count(), 7)

    def test_city_reading_uses_normalized_lemmas(self):
        reading = ReadingText.objects.get(id="droga-do-muzeum")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["drogę"]["lemma"], "droga")
        self.assertEqual(reading.glossary["skrzyżowaniu"]["lemma"], "skrzyżowanie")
        self.assertEqual(reading.glossary["wychodzi"]["part_of_speech"], "глагол")

    def test_catalog_lists_first_seven_curriculum_topics(self):
        self.assertEqual(
            [topic["id"] for topic in course_topics()[:7]],
            ["introductions", "countries-languages", "family", "daily-routine", "home", "food-shopping", "city-directions"],
        )


class TimeMeetingsContentTests(TestCase):
    def test_time_meetings_is_eighth_complete_topic(self):
        topic = Topic.objects.get(id="time-meetings")
        self.assertEqual(topic.position, 7)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="time-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="time-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="time-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="time-review").count(), 7)

    def test_time_reading_uses_normalized_lemmas(self):
        reading = ReadingText.objects.get(id="spotkanie-w-piatek")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["tygodniu"]["lemma"], "tydzień")
        self.assertEqual(reading.glossary["jedzie"]["lemma"], "jechać")
        self.assertEqual(reading.glossary["cieszą"]["lemma"], "cieszyć się")

    def test_catalog_lists_first_eight_curriculum_topics(self):
        self.assertEqual(
            [topic["id"] for topic in course_topics()[:8]],
            ["introductions", "countries-languages", "family", "daily-routine", "home", "food-shopping", "city-directions", "time-meetings"],
        )


class WorkStudyContentTests(TestCase):
    def test_work_study_is_ninth_complete_topic(self):
        topic = Topic.objects.get(id="work-study")
        self.assertEqual(topic.position, 8)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="work-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="work-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="work-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="work-review").count(), 7)

    def test_work_reading_uses_normalized_lemmas(self):
        reading = ReadingText.objects.get(id="pierwszy-dzien-w-pracy")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["pracowników"]["lemma"], "pracownik")
        self.assertEqual(reading.glossary["zmęczona"]["lemma"], "zmęczony")
        self.assertEqual(reading.glossary["rozumie"]["lemma"], "rozumieć")

    def test_catalog_lists_first_nine_curriculum_topics(self):
        self.assertEqual(
            [topic["id"] for topic in course_topics()[:9]],
            ["introductions", "countries-languages", "family", "daily-routine", "home", "food-shopping", "city-directions", "time-meetings", "work-study"],
        )


class FreeTimeContentTests(TestCase):
    def test_free_time_is_tenth_complete_topic(self):
        topic = Topic.objects.get(id="free-time")
        self.assertEqual(topic.position, 9)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="free-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="free-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="free-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="free-review").count(), 7)

    def test_free_time_reading_uses_normalized_lemmas(self):
        reading = ReadingText.objects.get(id="wolna-sobota-marka")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["przyjaciółmi"]["lemma"], "przyjaciel")
        self.assertEqual(reading.glossary["jeżdżą"]["lemma"], "jeździć")
        self.assertEqual(reading.glossary["woli"]["lemma"], "woleć")

    def test_catalog_lists_first_ten_curriculum_topics(self):
        self.assertEqual(
            [topic["id"] for topic in course_topics()[:10]],
            ["introductions", "countries-languages", "family", "daily-routine", "home", "food-shopping", "city-directions", "time-meetings", "work-study", "free-time"],
        )


class HealthContentTests(TestCase):
    def test_health_is_eleventh_complete_topic(self):
        topic = Topic.objects.get(id="health")
        self.assertEqual(topic.position, 10)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="health-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="health-quiz").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="health-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="health-review").count(), 7)

    def test_health_reading_has_original_metadata_and_normalized_lemmas(self):
        reading = ReadingText.objects.get(id="ola-u-lekarza")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["czuje"]["lemma"], "czuć się")
        self.assertEqual(reading.glossary["receptę"]["lemma"], "recepta")
        self.assertEqual(reading.glossary["odpoczywa"]["lemma"], "odpoczywać")

    def test_catalog_lists_first_eleven_curriculum_topics(self):
        self.assertEqual(
            [topic["id"] for topic in course_topics()[:11]],
            [
                "introductions", "countries-languages", "family", "daily-routine",
                "home", "food-shopping", "city-directions", "time-meetings",
                "work-study", "free-time", "health",
            ],
        )


class A1FinalReviewContentTests(TestCase):
    def test_final_review_is_twelfth_complete_topic(self):
        topic = Topic.objects.get(id="a1-final-review")
        self.assertEqual(topic.position, 11)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="final-grammar").count(), 6)
        self.assertEqual(Question.objects.filter(lesson_id="final-quiz").count(), 12)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="final-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="final-review").count(), 8)

    def test_final_reading_is_original_and_uses_normalized_lemmas(self):
        reading = ReadingText.objects.get(id="samodzielny-dzien-leny")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["umawia"]["lemma"], "umawiać się")
        self.assertEqual(reading.glossary["sprzedawcę"]["lemma"], "sprzedawca")
        self.assertEqual(reading.glossary["załatwiła"]["lemma"], "załatwić")

    def test_a1_catalog_has_all_twelve_curriculum_topics(self):
        topics = course_topics()
        self.assertEqual(len([topic for topic in topics if topic["level"] == "A1"]), 12)
        self.assertEqual(topics[11]["id"], "a1-final-review")


class A2PastWeekendContentTests(TestCase):
    def test_past_weekend_is_first_complete_a2_topic(self):
        course = Course.objects.get(id="a2-independence")
        topic = Topic.objects.get(id="past-weekend")
        self.assertEqual(course.level, "A2")
        self.assertEqual(topic.course, course)
        self.assertEqual(topic.position, 0)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="past-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="past-quiz").count(), 8)
        self.assertEqual(
            Question.objects.filter(lesson_id="weekend-reading-check").count(), 5
        )
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="past-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="past-review").count(), 7)

    def test_a2_reading_has_original_metadata_and_normalized_lemmas(self):
        reading = ReadingText.objects.get(id="weekend-kasi-i-pawla")
        self.assertEqual(reading.level, "A2")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(
            reading.source_metadata["comprehension_lesson_id"],
            "weekend-reading-check",
        )
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["pojechała"]["lemma"], "pojechać")
        self.assertEqual(reading.glossary["poszły"]["lemma"], "pójść")
        self.assertEqual(reading.glossary["odpoczął"]["lemma"], "odpocząć")

    def test_catalog_starts_a2_with_past_weekend(self):
        a2_topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual(a2_topics[0]["id"], "past-weekend")
        self.assertEqual(len(a2_topics[0]["lessons"]), 5)


class A2TravelPlansContentTests(TestCase):
    def test_travel_plans_is_second_complete_a2_topic(self):
        topic = Topic.objects.get(id="travel-plans")
        self.assertEqual(topic.course_id, "a2-independence")
        self.assertEqual(topic.position, 1)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="travel-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="travel-quiz").count(), 8)
        self.assertEqual(Question.objects.filter(lesson_id="travel-reading-check").count(), 5)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="travel-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="travel-review").count(), 7)

    def test_travel_reading_is_lemma_aware_and_links_comprehension(self):
        reading = ReadingText.objects.get(id="plan-wyjazdu-do-gdanska")
        self.assertEqual(reading.level, "A2")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "travel-reading-check")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["pojadą"]["lemma"], "pojechać")
        self.assertEqual(reading.glossary["przesiądą"]["lemma"], "przesiąść się")
        self.assertEqual(reading.glossary["starówki"]["lemma"], "starówka")

    def test_catalog_lists_both_a2_topics_in_order(self):
        a2_topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual([topic["id"] for topic in a2_topics[:2]], ["past-weekend", "travel-plans"])
        self.assertEqual([len(topic["lessons"]) for topic in a2_topics[:2]], [5, 5])


class A2HousingServicesContentTests(TestCase):
    def test_housing_services_is_third_complete_a2_topic(self):
        topic = Topic.objects.get(id="housing-services")
        self.assertEqual(topic.course_id, "a2-independence")
        self.assertEqual(topic.position, 2)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="housing-grammar").count(), 7)
        self.assertEqual(Question.objects.filter(lesson_id="housing-quiz").count(), 8)
        self.assertEqual(Question.objects.filter(lesson_id="housing-reading-check").count(), 5)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="housing-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="housing-review").count(), 7)

    def test_housing_reading_is_lemma_aware_and_links_comprehension(self):
        reading = ReadingText.objects.get(id="usterka-w-mieszkaniu")
        self.assertEqual(reading.level, "A2")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "housing-reading-check")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["kaloryfery"]["lemma"], "kaloryfer")
        self.assertEqual(reading.glossary["usterki"]["lemma"], "usterka")
        self.assertEqual(reading.glossary["spóźni"]["lemma"], "spóźnić się")

    def test_catalog_lists_three_a2_topics_in_order(self):
        a2_topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual(
            [topic["id"] for topic in a2_topics[:3]],
            ["past-weekend", "travel-plans", "housing-services"],
        )
        self.assertEqual([len(topic["lessons"]) for topic in a2_topics[:3]], [5, 5, 5])


class A2WorkContentTests(TestCase):
    def test_work_is_fourth_complete_a2_topic(self):
        topic = Topic.objects.get(id="a2-work")
        self.assertEqual(topic.position, 3)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="a2work-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="a2work-quiz").count(), 8)
        self.assertEqual(Question.objects.filter(lesson_id="a2work-reading-check").count(), 5)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="a2work-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="a2work-review").count(), 7)

    def test_work_reading_is_original_and_lemma_aware(self):
        reading = ReadingText.objects.get(id="pierwszy-tydzien-mai")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "a2work-reading-check")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["obsłudze"]["lemma"], "obsługa")
        self.assertEqual(reading.glossary["wykonała"]["lemma"], "wykonać")

    def test_catalog_lists_four_a2_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual([topic["id"] for topic in topics[:4]], ["past-weekend", "travel-plans", "housing-services", "a2-work"])


class A2ShoppingReturnsContentTests(TestCase):
    def test_shopping_returns_is_fifth_complete_a2_topic(self):
        topic = Topic.objects.get(id="shopping-returns")
        self.assertEqual(topic.position, 4)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="returns-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="returns-quiz").count(), 8)
        self.assertEqual(Question.objects.filter(lesson_id="returns-reading-check").count(), 5)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="returns-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="returns-review").count(), 7)

    def test_returns_reading_has_lemma_aware_glossary(self):
        reading = ReadingText.objects.get(id="reklamacja-natalii")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "returns-reading-check")
        self.assertEqual(reading.glossary["wyprzedaży"]["lemma"], "wyprzedaż")
        self.assertEqual(reading.glossary["wymianę"]["lemma"], "wymiana")

    def test_catalog_lists_five_a2_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual([topic["id"] for topic in topics[:5]], ["past-weekend", "travel-plans", "housing-services", "a2-work", "shopping-returns"])


class A2DoctorPharmacyContentTests(TestCase):
    def test_doctor_pharmacy_is_sixth_complete_a2_topic(self):
        topic = Topic.objects.get(id="doctor-pharmacy")
        self.assertEqual(topic.position, 5)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="med-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="med-quiz").count(), 8)
        self.assertEqual(Question.objects.filter(lesson_id="med-reading-check").count(), 5)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="med-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="med-review").count(), 7)

    def test_medical_reading_is_original_and_lemma_aware(self):
        reading = ReadingText.objects.get(id="adam-u-lekarza-i-w-aptece")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "med-reading-check")
        self.assertEqual(reading.glossary["płuca"]["lemma"], "płuco")
        self.assertEqual(reading.glossary["pogorszy"]["lemma"], "pogorszyć się")

    def test_catalog_lists_six_a2_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual([topic["id"] for topic in topics[:6]], ["past-weekend", "travel-plans", "housing-services", "a2-work", "shopping-returns", "doctor-pharmacy"])


class A2RelationshipsEmotionsContentTests(TestCase):
    def test_relationships_emotions_is_seventh_complete_a2_topic(self):
        topic = Topic.objects.get(id="relationships-emotions")
        self.assertEqual(topic.position, 6)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="rel-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="rel-quiz").count(), 8)
        self.assertEqual(Question.objects.filter(lesson_id="rel-reading-check").count(), 5)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="rel-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="rel-review").count(), 7)

    def test_relationships_reading_is_original_and_lemma_aware(self):
        reading = ReadingText.objects.get(id="szczera-rozmowa-marty-i-ani")
        self.assertEqual(reading.level, "A2")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "rel-reading-check")
        self.assertEqual(len(reading.paragraphs), 3)
        self.assertEqual(reading.glossary["przyjaźnią"]["lemma"], "przyjaźnić się")
        self.assertEqual(reading.glossary["uspokoić"]["lemma"], "uspokoić się")
        self.assertEqual(reading.glossary["odbudowała"]["lemma"], "odbudować")

    def test_catalog_lists_seven_a2_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual(
            [topic["id"] for topic in topics[:7]],
            ["past-weekend", "travel-plans", "housing-services", "a2-work", "shopping-returns", "doctor-pharmacy", "relationships-emotions"],
        )


class A2CultureMediaContentTests(TestCase):
    def test_culture_media_is_eighth_complete_a2_topic(self):
        topic = Topic.objects.get(id="culture-media")
        self.assertEqual(topic.position, 7)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="culture-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="culture-quiz").count(), 8)
        self.assertEqual(Question.objects.filter(lesson_id="culture-reading-check").count(), 5)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="culture-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="culture-review").count(), 7)

    def test_culture_reading_is_original_and_lemma_aware(self):
        reading = ReadingText.objects.get(id="wieczor-krotkich-filmow")
        self.assertEqual(reading.level, "A2")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "culture-reading-check")
        self.assertEqual(reading.glossary["reżyserów"]["lemma"], "reżyser")
        self.assertEqual(reading.glossary["reżyserką"]["lemma"], "reżyserka")
        self.assertEqual(reading.glossary["zachęciły"]["lemma"], "zachęcić")

    def test_catalog_lists_eight_a2_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual(
            [topic["id"] for topic in topics[:8]],
            ["past-weekend", "travel-plans", "housing-services", "a2-work", "shopping-returns", "doctor-pharmacy", "relationships-emotions", "culture-media"],
        )


class A2InstitutionsContentTests(TestCase):
    def test_institutions_is_ninth_complete_a2_topic(self):
        topic = Topic.objects.get(id="institutions")
        self.assertEqual(topic.position, 8)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="office-grammar").count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="office-quiz").count(), 8)
        self.assertEqual(Question.objects.filter(lesson_id="office-reading-check").count(), 5)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="office-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="office-review").count(), 7)

    def test_institutions_reading_is_original_and_lemma_aware(self):
        reading = ReadingText.objects.get(id="natalia-sklada-wniosek")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "office-reading-check")
        self.assertEqual(reading.glossary["ważności"]["lemma"], "ważność")
        self.assertEqual(reading.glossary["rubryce"]["lemma"], "rubryka")
        self.assertEqual(reading.glossary["wniosku"]["lemma"], "wniosek")

    def test_catalog_lists_nine_a2_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual(
            [topic["id"] for topic in topics[:9]],
            ["past-weekend", "travel-plans", "housing-services", "a2-work", "shopping-returns", "doctor-pharmacy", "relationships-emotions", "culture-media", "institutions"],
        )


class A2CompletionContentTests(TestCase):
    def test_remaining_topics_have_complete_lesson_sets(self):
        expectations = (
            ("weather-nature", 9, "weather", 5, 8, 5),
            ("poland-around-us", 10, "poland", 5, 8, 5),
            ("a2final-review", 11, "a2final", 8, 12, 6),
        )
        for topic_id, position, prefix, grammar_count, quiz_count, reading_count in expectations:
            with self.subTest(topic_id=topic_id):
                topic = Topic.objects.get(id=topic_id)
                self.assertEqual(topic.position, position)
                self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
                grammar_id = f"{prefix}-diagnosis" if prefix == "a2final" else f"{prefix}-grammar"
                self.assertEqual(Question.objects.filter(lesson_id=grammar_id).count(), grammar_count)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-quiz").count(), quiz_count)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-reading-check").count(), reading_count)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-words").count(), 8)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-review").count(), 8 if prefix == "a2final" else 7)

    def test_new_readings_are_original_and_lemma_aware(self):
        expectations = (
            ("weather-wycieczka-przed-burza", "weather-reading-check", "wzgórza", "wzgórze"),
            ("poland-maja-odkrywa-torun", "poland-reading-check", "przewodniczką", "przewodniczka"),
            ("a2final-weekend-leny", "a2final-reading-check", "kłótni", "kłótnia"),
        )
        for reading_id, lesson_id, surface, lemma in expectations:
            with self.subTest(reading_id=reading_id):
                reading = ReadingText.objects.get(id=reading_id)
                self.assertEqual(reading.level, "A2")
                self.assertEqual(reading.source_metadata["origin"], "original")
                self.assertEqual(reading.source_metadata["comprehension_lesson_id"], lesson_id)
                self.assertEqual(reading.glossary[surface]["lemma"], lemma)

    def test_a2_catalog_is_complete(self):
        topics = [topic for topic in course_topics() if topic["level"] == "A2"]
        self.assertEqual(
            [topic["id"] for topic in topics],
            [
                "past-weekend", "travel-plans", "housing-services", "a2-work",
                "shopping-returns", "doctor-pharmacy", "relationships-emotions",
                "culture-media", "institutions", "weather-nature",
                "poland-around-us", "a2final-review",
            ],
        )


class B2SecondTopicsContentTests(TestCase):
    def test_topics_five_through_eight_have_complete_vertical_lesson_sets(self):
        expectations = (
            ("b2-economy-consumption", 4, "b2economy"),
            ("b2-law-civic", 5, "b2law"),
            ("b2-psychology-relationships", 6, "b2psych"),
            ("b2-literature-cinema", 7, "b2lit"),
        )
        for topic_id, position, prefix in expectations:
            with self.subTest(topic_id=topic_id):
                topic = Topic.objects.get(id=topic_id)
                self.assertEqual(topic.course.level, "B2")
                self.assertEqual(topic.position, position)
                self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-grammar").count(), 6)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-quiz").count(), 10)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-reading-check").count(), 6)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-words").count(), 8)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-review").count(), 7)

    def test_new_readings_are_original_and_lemma_aware(self):
        expectations = (
            ("b2economy-subskrypcja-czy-zakup", "b2economy-reading-check"),
            ("b2law-odwolanie-od-decyzji", "b2law-reading-check"),
            ("b2psych-rozmowa-po-nieudanym-wyjezdzie", "b2psych-reading-check"),
            ("b2lit-recenzja-filmu-swiatlo-na-peronie", "b2lit-reading-check"),
        )
        for reading_id, lesson_id in expectations:
            with self.subTest(reading_id=reading_id):
                reading = ReadingText.objects.get(id=reading_id)
                self.assertEqual(reading.level, "B2")
                self.assertEqual(reading.source_metadata["origin"], "original")
                self.assertEqual(reading.source_metadata["comprehension_lesson_id"], lesson_id)
                self.assertGreaterEqual(len(reading.paragraphs), 4)
                self.assertGreaterEqual(len(reading.glossary), 18)
                for entry in reading.glossary.values():
                    self.assertTrue(entry["lemma"])
                    self.assertTrue(entry["translation"])
                    self.assertTrue(entry["part_of_speech"])

    def test_b2_catalog_lists_all_topics_in_order(self):
        topics = [topic for topic in course_topics() if topic["level"] == "B2"]
        self.assertEqual(
            [topic["id"] for topic in topics],
            [
                "b2-viewpoints", "b2-news", "b2-professional-communication",
                "b2-science-technology", "b2-economy-consumption", "b2-law-civic",
                "b2-psychology-relationships", "b2-literature-cinema",
                "b2-public-discussion", "b2-intercultural-communication",
                "b2-academic-skills", "b2-final-project",
            ],
        )


class B1BiographyContentTests(TestCase):
    def test_biography_is_first_complete_b1_topic(self):
        topic = Topic.objects.get(id="b1-biography")
        self.assertEqual(topic.course.level, "B1")
        self.assertEqual(topic.position, 0)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="bio-grammar").count(), 6)
        self.assertEqual(Question.objects.filter(lesson_id="bio-quiz").count(), 10)
        self.assertEqual(Question.objects.filter(lesson_id="bio-reading-check").count(), 6)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="bio-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="bio-review").count(), 7)

    def test_biography_reading_is_original_and_lemma_aware(self):
        reading = ReadingText.objects.get(id="bio-droga-joanny")
        self.assertEqual(reading.level, "B1")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "bio-reading-check")
        self.assertEqual(len(reading.paragraphs), 4)
        self.assertEqual(reading.glossary["dorastała"]["lemma"], "dorastać")
        self.assertEqual(reading.glossary["punktem zwrotnym"]["lemma"], "punkt zwrotny")

    def test_catalog_starts_b1_with_biography(self):
        topics = [topic for topic in course_topics() if topic["level"] == "B1"]
        self.assertEqual([topic["id"] for topic in topics[:1]], ["b1-biography"])


class B1TravelContentTests(TestCase):
    def test_travel_is_second_complete_b1_topic(self):
        topic = Topic.objects.get(id="b1-travel")
        self.assertEqual(topic.position, 1)
        self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
        self.assertEqual(Question.objects.filter(lesson_id="b1trip-grammar").count(), 6)
        self.assertEqual(Question.objects.filter(lesson_id="b1trip-quiz").count(), 10)
        self.assertEqual(Question.objects.filter(lesson_id="b1trip-reading-check").count(), 6)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="b1trip-words").count(), 8)
        self.assertEqual(LessonFlashcard.objects.filter(lesson_id="b1trip-review").count(), 7)

    def test_travel_reading_is_original_and_lemma_aware(self):
        reading = ReadingText.objects.get(id="b1trip-nieplanowana-przesiadka")
        self.assertEqual(reading.level, "B1")
        self.assertEqual(reading.source_metadata["origin"], "original")
        self.assertEqual(reading.source_metadata["comprehension_lesson_id"], "b1trip-reading-check")
        self.assertEqual(reading.glossary["zdążą"]["lemma"], "zdążyć")
        self.assertEqual(reading.glossary["przechowalni"]["lemma"], "przechowalnia")

    def test_catalog_lists_two_b1_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "B1"]
        self.assertEqual([topic["id"] for topic in topics[:2]], ["b1-biography", "b1-travel"])


class B1WorkEducationContentTests(TestCase):
    def test_topics_have_complete_lesson_sets(self):
        expectations = (
            ("b1-work-development", 2, "b1work"),
            ("b1-education", 3, "b1edu"),
        )
        for topic_id, position, prefix in expectations:
            with self.subTest(topic_id=topic_id):
                topic = Topic.objects.get(id=topic_id)
                self.assertEqual(topic.course.level, "B1")
                self.assertEqual(topic.position, position)
                self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-grammar").count(), 6)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-quiz").count(), 10)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-reading-check").count(), 6)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-words").count(), 8)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-review").count(), 7)

    def test_readings_are_original_and_lemma_aware(self):
        expectations = (
            ("b1work-nowy-krok-leny", "b1work-reading-check", "ustaliłaby", "ustalić", 14),
            ("b1edu-kurs-ktory-zmienil-sposob-nauki", "b1edu-reading-check", "rozmówców", "rozmówca", 16),
        )
        for reading_id, lesson_id, surface, lemma, glossary_size in expectations:
            with self.subTest(reading_id=reading_id):
                reading = ReadingText.objects.get(id=reading_id)
                self.assertEqual(reading.level, "B1")
                self.assertEqual(reading.source_metadata["origin"], "original")
                self.assertEqual(reading.source_metadata["comprehension_lesson_id"], lesson_id)
                self.assertEqual(len(reading.paragraphs), 4)
                self.assertEqual(len(reading.glossary), glossary_size)
                self.assertEqual(reading.glossary[surface]["lemma"], lemma)

    def test_catalog_lists_four_b1_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "B1"]
        self.assertEqual(
            [topic["id"] for topic in topics[:4]],
            ["b1-biography", "b1-travel", "b1-work-development", "b1-education"],
        )


class B1RelationshipsThroughCultureContentTests(TestCase):
    def test_four_topics_have_complete_vertical_lesson_sets(self):
        expectations = (
            ("b1-relationships", 4, "b1rel"),
            ("b1-healthy-lifestyle", 5, "b1health"),
            ("b1-media-internet", 6, "b1media"),
            ("b1-culture", 7, "b1culture"),
        )
        for topic_id, position, prefix in expectations:
            with self.subTest(topic_id=topic_id):
                topic = Topic.objects.get(id=topic_id)
                self.assertEqual(topic.course.level, "B1")
                self.assertEqual(topic.position, position)
                self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-grammar").count(), 6)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-quiz").count(), 10)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-reading-check").count(), 6)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-words").count(), 8)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-review").count(), 7)

    def test_four_readings_are_original_and_lemma_aware(self):
        expectations = (
            ("b1rel-weekend-na-dwa-sposoby", "b1rel-reading-check"),
            ("b1health-maly-krok-kuby", "b1health-reading-check"),
            ("b1media-wiadomosc-ktora-wymagala-sprawdzenia", "b1media-reading-check"),
            ("b1culture-wieczor-z-ksiazka-i-filmem", "b1culture-reading-check"),
        )
        for reading_id, lesson_id in expectations:
            with self.subTest(reading_id=reading_id):
                reading = ReadingText.objects.get(id=reading_id)
                self.assertEqual(reading.level, "B1")
                self.assertEqual(reading.source_metadata["origin"], "original")
                self.assertEqual(reading.source_metadata["comprehension_lesson_id"], lesson_id)
                self.assertEqual(len(reading.paragraphs), 4)
                self.assertGreaterEqual(len(reading.glossary), 14)
                for entry in reading.glossary.values():
                    self.assertTrue(entry["lemma"])
                    self.assertTrue(entry["translation"])
                    self.assertTrue(entry["part_of_speech"])

    def test_catalog_lists_eight_b1_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "B1"]
        self.assertEqual(
            [topic["id"] for topic in topics[:8]],
            [
                "b1-biography", "b1-travel", "b1-work-development", "b1-education",
                "b1-relationships", "b1-healthy-lifestyle", "b1-media-internet", "b1-culture",
            ],
        )


class B1CompletionContentTests(TestCase):
    def test_final_four_topics_have_complete_vertical_lesson_sets(self):
        expectations = (
            ("b1-society", 8, "b1soc"),
            ("b1-ecology", 9, "b1eco"),
            ("b1-poland-regions", 10, "b1region"),
            ("b1-final-project", 11, "b1final"),
        )
        for topic_id, position, prefix in expectations:
            with self.subTest(topic_id=topic_id):
                topic = Topic.objects.get(id=topic_id)
                self.assertEqual(topic.course.level, "B1")
                self.assertEqual(topic.position, position)
                self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-grammar").count(), 6)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-quiz").count(), 10)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-reading-check").count(), 6)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-words").count(), 8)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-review").count(), 7)

    def test_final_readings_are_original_and_lemma_aware(self):
        expectations = (
            ("b1soc-sasiedzki-ogrod", "b1soc-reading-check"),
            ("b1eco-rzeka-wraca-do-miasta", "b1eco-reading-check"),
            ("b1region-dwa-spojrzenia-na-beskid", "b1region-reading-check"),
            ("b1final-projekt-marty", "b1final-reading-check"),
        )
        for reading_id, lesson_id in expectations:
            with self.subTest(reading_id=reading_id):
                reading = ReadingText.objects.get(id=reading_id)
                self.assertEqual(reading.level, "B1")
                self.assertEqual(reading.source_metadata["origin"], "original")
                self.assertEqual(reading.source_metadata["comprehension_lesson_id"], lesson_id)
                self.assertEqual(len(reading.paragraphs), 4)
                self.assertGreaterEqual(len(reading.glossary), 14)
                for entry in reading.glossary.values():
                    self.assertTrue(entry["lemma"])
                    self.assertTrue(entry["translation"])
                    self.assertTrue(entry["part_of_speech"])

    def test_b1_catalog_is_complete(self):
        topics = [topic for topic in course_topics() if topic["level"] == "B1"]
        self.assertEqual(
            [topic["id"] for topic in topics],
            [
                "b1-biography", "b1-travel", "b1-work-development", "b1-education",
                "b1-relationships", "b1-healthy-lifestyle", "b1-media-internet", "b1-culture",
                "b1-society", "b1-ecology", "b1-poland-regions", "b1-final-project",
            ],
        )


class B2FirstTopicsContentTests(TestCase):
    def test_first_four_topics_have_complete_vertical_lesson_sets(self):
        expectations = (
            ("b2-viewpoints", 0, "b2view"),
            ("b2-news", 1, "b2news"),
            ("b2-professional-communication", 2, "b2prof"),
            ("b2-science-technology", 3, "b2tech"),
        )
        for topic_id, position, prefix in expectations:
            with self.subTest(topic_id=topic_id):
                topic = Topic.objects.get(id=topic_id)
                self.assertEqual(topic.course.level, "B2")
                self.assertEqual(topic.position, position)
                self.assertEqual(Lesson.objects.filter(topic=topic).count(), 5)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-grammar").count(), 6)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-quiz").count(), 10)
                self.assertEqual(Question.objects.filter(lesson_id=f"{prefix}-reading-check").count(), 6)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-words").count(), 8)
                self.assertEqual(LessonFlashcard.objects.filter(lesson_id=f"{prefix}-review").count(), 7)

    def test_first_four_readings_are_original_and_lemma_aware(self):
        expectations = (
            ("b2view-debata-o-spokojnym-centrum", "b2view-reading-check"),
            ("b2news-trzy-relacje-o-jednej-awarii", "b2news-reading-check"),
            ("b2prof-spotkanie-ktore-konczy-sie-decyzja", "b2prof-reading-check"),
            ("b2tech-czujniki-ktore-oszczedzaja-wode", "b2tech-reading-check"),
        )
        for reading_id, lesson_id in expectations:
            with self.subTest(reading_id=reading_id):
                reading = ReadingText.objects.get(id=reading_id)
                self.assertEqual(reading.level, "B2")
                self.assertEqual(reading.source_metadata["origin"], "original")
                self.assertEqual(reading.source_metadata["comprehension_lesson_id"], lesson_id)
                self.assertGreaterEqual(len(reading.paragraphs), 4)
                self.assertGreaterEqual(len(reading.glossary), 16)
                for entry in reading.glossary.values():
                    self.assertTrue(entry["lemma"])
                    self.assertTrue(entry["translation"])
                    self.assertTrue(entry["part_of_speech"])

    def test_b2_catalog_starts_with_four_complete_topics(self):
        topics = [topic for topic in course_topics() if topic["level"] == "B2"]
        self.assertEqual(
            [topic["id"] for topic in topics[:4]],
            [
                "b2-viewpoints",
                "b2-news",
                "b2-professional-communication",
                "b2-science-technology",
            ],
        )
