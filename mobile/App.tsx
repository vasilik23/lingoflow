import { useEffect, useState } from 'react';
import { AppState, SafeAreaView, StyleSheet, useColorScheme } from 'react-native';
import type { Session } from '@supabase/supabase-js';
import { StatusBar } from 'expo-status-bar';

import { LoginScreen } from './src/components/LoginScreen';
import { TodayScreen } from './src/components/TodayScreen';
import { LessonScreen } from './src/components/LessonScreen';
import { FeedbackScreen } from './src/components/FeedbackScreen';
import { ReviewScreen } from './src/components/ReviewScreen';
import { ReadingScreen } from './src/components/ReadingScreen';
import { ListeningScreen } from './src/components/ListeningScreen';
import { ProfileScreen } from './src/components/ProfileScreen';
import { AchievementsScreen } from './src/components/AchievementsScreen';
import { HistoryScreen } from './src/components/HistoryScreen';
import { DiagnosticScreen } from './src/components/DiagnosticScreen';
import { WritingScreen } from './src/components/WritingScreen';
import { InteractionScreen } from './src/components/InteractionScreen';
import { PracticeScreen } from './src/components/PracticeScreen';
import { supabase } from './src/lib/supabase';
import { palette } from './src/theme';

export default function App() {
  const dark = useColorScheme() === 'dark';
  const colors = palette(dark);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [lessonLaunch, setLessonLaunch] = useState<{ lessonId: string; stepIndex: number; score: number } | null>(null);
  const [screen, setScreen] = useState<'today' | 'practice' | 'feedback' | 'review' | 'reading' | 'listening' | 'profile' | 'achievements' | 'history' | 'diagnostic' | 'writing' | 'interaction'>('today');

  useEffect(() => {
    let mounted = true;
    void supabase.auth.getSession().then(({ data }) => {
      if (mounted) { setSession(data.session); setLoading(false); }
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next); setLoading(false);
    });
    const appState = AppState.addEventListener('change', (state) => {
      if (state === 'active') supabase.auth.startAutoRefresh();
      else supabase.auth.stopAutoRefresh();
    });
    supabase.auth.startAutoRefresh();
    return () => {
      mounted = false; listener.subscription.unsubscribe(); appState.remove(); supabase.auth.stopAutoRefresh();
    };
  }, []);

  return (
    <SafeAreaView style={[styles.shell, { backgroundColor: colors.background }]}>
      <StatusBar style={dark ? 'light' : 'dark'} />
      {session ? (lessonLaunch
        ? <LessonScreen {...lessonLaunch} session={session} colors={colors} onClose={() => setLessonLaunch(null)} />
        : screen === 'feedback'
          ? <FeedbackScreen session={session} colors={colors} onClose={() => setScreen('today')} />
          : screen === 'practice'
            ? <PracticeScreen key={session.user.id} session={session} colors={colors} onClose={() => setScreen('today')} onOpen={setScreen} />
          : screen === 'review'
            ? <ReviewScreen session={session} colors={colors} onClose={() => setScreen('today')} />
            : screen === 'reading'
              ? <ReadingScreen session={session} colors={colors} onClose={() => setScreen('today')} onOpenLesson={(lessonId) => setLessonLaunch({ lessonId, stepIndex: 0, score: 0 })} />
              : screen === 'listening'
                ? <ListeningScreen session={session} colors={colors} onClose={() => setScreen('today')} />
                : screen === 'profile'
                  ? <ProfileScreen session={session} colors={colors} onClose={() => setScreen('today')} />
                  : screen === 'achievements'
                    ? <AchievementsScreen session={session} colors={colors} onClose={() => setScreen('today')} />
                    : screen === 'history'
                      ? <HistoryScreen session={session} colors={colors} onClose={() => setScreen('today')} />
                      : screen === 'diagnostic'
                        ? <DiagnosticScreen session={session} colors={colors} onClose={() => setScreen('today')} />
                        : screen === 'writing'
                          ? <WritingScreen session={session} colors={colors} onClose={() => setScreen('today')} />
                          : screen === 'interaction'
                            ? <InteractionScreen session={session} colors={colors} onClose={() => setScreen('today')} />
                            : <TodayScreen session={session} colors={colors} onOpenLesson={(lessonId) => setLessonLaunch({ lessonId, stepIndex: 0, score: 0 })} onResumeLesson={setLessonLaunch} onOpenFeedback={() => setScreen('feedback')} onOpenReview={() => setScreen('review')} onOpenProfile={() => setScreen('profile')} onOpenPractice={() => setScreen('practice')} />
      ) : <LoginScreen colors={colors} booting={loading} />}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({ shell: { flex: 1 } });
