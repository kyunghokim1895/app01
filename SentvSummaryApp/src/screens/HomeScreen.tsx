import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text, FlatList, TouchableOpacity, TextInput, ActivityIndicator } from 'react-native';
import SummaryCard from '../components/SummaryCard';
import { fetchSummaries } from '../services/dataService';

const DUMMY_KEYWORDS = ['#부동산', '#삼성전자', '#코스피', '#금리', '#나스닥', '#가상화폐'];

const HomeScreen = ({ navigation }: any) => {
    const [search, setSearch] = useState('');
    const [selectedKeyword, setSelectedKeyword] = useState('');
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        const result = await fetchSummaries();
        setData(result);
        setLoading(false);
    };

    const filteredData = data.filter(item => {
        const matchesSearch = item.title.includes(search) || item.summary.includes(search);
        const matchesKeyword = selectedKeyword ? item.keywords.includes(selectedKeyword) : true;
        return matchesSearch && matchesKeyword;
    });

    return (
        <View style={styles.container}>
            {/* 키워드 검색 및 선택 영역 */}
            <View style={styles.headerSection}>
                <TextInput
                    style={styles.searchInput}
                    placeholder="관심 키워드를 입력하세요"
                    placeholderTextColor="#888"
                    value={search}
                    onChangeText={setSearch}
                />
                <FlatList
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    data={DUMMY_KEYWORDS}
                    keyExtractor={(item) => item}
                    style={styles.keywordList}
                    renderItem={({ item }) => (
                        <TouchableOpacity
                            style={[
                                styles.keywordChip,
                                selectedKeyword === item && styles.selectedChip
                            ]}
                            onPress={() => setSelectedKeyword(item === selectedKeyword ? '' : item)}
                        >
                            <Text style={[
                                styles.keywordText,
                                selectedKeyword === item && styles.selectedKeywordText
                            ]}>{item}</Text>
                        </TouchableOpacity>
                    )}
                />
            </View>

            {/* 요약 목록 영역 */}
            {loading ? (
                <View style={styles.loader}>
                    <ActivityIndicator size="large" color="#1a1a1a" />
                    <Text style={styles.loaderText}>최신 요약을 불러오는 중...</Text>
                </View>
            ) : (
                <FlatList
                    data={filteredData}
                    keyExtractor={(item) => item.id}
                    contentContainerStyle={{ paddingBottom: 200 }}
                    renderItem={({ item }) => (
                        <SummaryCard item={item} onPress={() => navigation.navigate('Detail', { item })} />
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
    searchInput: {
        height: 45,
        backgroundColor: '#f5f5f5',
        borderRadius: 10,
        paddingHorizontal: 15,
        marginBottom: 10,
        fontSize: 16,
        color: '#333',
    },
    keywordList: {
        flexDirection: 'row',
    },
    keywordChip: {
        paddingHorizontal: 15,
        paddingVertical: 8,
        backgroundColor: '#f0f0f0',
        borderRadius: 20,
        marginRight: 8,
    },
    selectedChip: {
        backgroundColor: '#1a1a1a',
    },
    keywordText: {
        color: '#666',
        fontWeight: '500',
    },
    selectedKeywordText: {
        color: '#fff',
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
