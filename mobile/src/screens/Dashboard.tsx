import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function Dashboard() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>CapitalGuard Algo Trader</Text>
      <Text style={styles.subtitle}>Capital-preserving index options – Upstox</Text>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Market Context</Text>
        <Text>Live index, EMA20/200, CPR, bias – placeholder.</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Signal Panel</Text>
        <Text>Signal status, reason, risk checklist – placeholder.</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Open Positions</Text>
        <Text>Symbol, entry, P&L – placeholder.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  title: { fontSize: 22, fontWeight: 'bold' },
  subtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  section: { marginTop: 24 },
  sectionTitle: { fontSize: 16, fontWeight: '600', marginBottom: 8 },
});
