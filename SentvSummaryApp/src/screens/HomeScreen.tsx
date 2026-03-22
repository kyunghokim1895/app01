import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text, FlatList, TouchableOpacity, TextInput, ActivityIndicator } from 'react-native';
import SummaryCard from '../components/SummaryCard';
import { fetchSummaries } from '../services/dataService';

const CATEGORIES = ['국내증시', '해외증시', '부동산', '가상자산', '경제정책', '산업/기업', '채권/환율', '재테크'];

const HomeScreen = ({ navigation }: any) => {
    const [search, setSearch] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('');
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
        const matchesSearch = search
            ? item.title.includes(search) || item.summary.includes(search)
            : true;
        const matchesCategory = selectedCategory
            ? item.category === selectedCategory
            : true;
        return matchesSearch && matchesCategory;
    });

    return (
        <View style={styles.container}>
            <View style={styles.headerSection}>
                <TextInput
                    style={styles.searchInput}
                    placeholder="검색어를 입력하세요"
                    placeholderTextColor="#888"
                    value={search}
                    onChangeText={setSearch}
                />
                <FlatList
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    data={CATEGORIES}
                    keyExtractor={(item) => item}
                    style={styles.categoryList}
                    renderItem={({ item }) => (
                        <TouchableOpacity
                            style={[
                                styles.categoryChip,
                                selectedCategory === item && styles.selectedChip
                            ]}
                            onPress={() => setSelectedCategory(item === selectedCategory ? '' : item)}
                        >
                            <Text style={[
                                styles.categoryText,
                                selectedCategory === item && styles.selectedCategoryText
                            ]}>{item}</Text>
                        </TouchableOpacity>
                    )}
                />
            </View>

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
    categoryList: {
        flexDirection: 'row',
    },
    categoryChip: {
        paddingHorizontal: 15,
        paddingVertical: 8,
        backgroundColor: '#f0f0f0',
        borderRadius: 20,
        marginRight: 8,
    },
    selectedChip: {
        backgroundColor: '#1a1a1a',
    },
    categoryText: {
        color: '#666',
        fontWeight: '500',
    },
    selectedCategoryText: {
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
