import React, { useState, useEffect, useCallback } from 'react';
import { StyleSheet, View, Text, FlatList, TouchableOpacity, TextInput, ActivityIndicator, Alert } from 'react-native';
import SummaryCard from '../components/SummaryCard';
import { fetchSummaries } from '../services/dataService';
import { theme } from '../constants/theme';

const HomeScreen = ({ navigation }: any) => {
    const [search, setSearch] = useState('');
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        const result = await fetchSummaries();

        if (result.length > 0 && data.length > 0 && result[0].id !== data[0].id) {
            Alert.alert('새 요약 도착', `'${result[0].title}' 등 새로운 핵심 요약이 업데이트되었습니다.`);
        }

        setData(result);
        setLoading(false);
    };

    const handleKeywordPress = useCallback((keyword: string) => {
        setSearch(keyword);
    }, []);

    const filteredData = data.filter(item => {
        if (!search) return true;
        return item.title.includes(search) ||
               item.summary.includes(search) ||
               (item.keywords && item.keywords.some((k: string) => k.includes(search)));
    });

    return (
        <View style={styles.container}>
            <View style={styles.headerSection}>
                <View style={styles.searchContainer}>
                    <TextInput
                        style={styles.searchInput}
                        placeholder="검색어를 입력하세요"
                        placeholderTextColor="#888"
                        value={search}
                        onChangeText={setSearch}
                    />
                    {search.length > 0 && (
                        <TouchableOpacity style={styles.clearButton} onPress={() => setSearch('')}>
                            <Text style={styles.clearButtonText}>✕</Text>
                        </TouchableOpacity>
                    )}
                </View>
            </View>

            {loading ? (
                <View style={styles.loader}>
                    <ActivityIndicator size="large" color={theme.primary} />
                    <Text style={styles.loaderText}>최신 요약을 불러오는 중...</Text>
                </View>
            ) : (
                <FlatList
                    data={filteredData}
                    keyExtractor={(item) => item.id}
                    contentContainerStyle={{ paddingBottom: 200 }}
                    renderItem={({ item }) => (
                        <SummaryCard
                            item={item}
                            onPress={() => navigation.navigate('Detail', { item })}
                            onKeywordPress={handleKeywordPress}
                        />
                    )}
                    ListEmptyComponent={
                        <View style={styles.emptyContainer}>
                            <Text style={styles.emptyText}>검색 결과가 없거나 요약된 내용이 없습니다.</Text>
                        </View>
                    }
                />
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
    },
    headerSection: {
        padding: 15,
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    searchContainer: {
        position: 'relative',
        justifyContent: 'center',
    },
    searchInput: {
        height: 45,
        backgroundColor: '#f5f5f5',
        borderRadius: 10,
        paddingHorizontal: 15,
        paddingRight: 40,
        fontSize: 16,
        color: '#333',
    },
    clearButton: {
        position: 'absolute',
        right: 12,
        width: 24,
        height: 24,
        borderRadius: 12,
        backgroundColor: '#ccc',
        justifyContent: 'center',
        alignItems: 'center',
    },
    clearButtonText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: 'bold',
    },
    loader: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loaderText: {
        marginTop: 10,
        color: '#666',
    },
    emptyContainer: {
        marginTop: 100,
        alignItems: 'center',
        justifyContent: 'center',
    },
    emptyText: {
        color: '#999',
        fontSize: 14,
    }
});

export default HomeScreen;
