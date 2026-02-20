import React from 'react';
import { StyleSheet, View, Text, ScrollView, TouchableOpacity, Linking, Share } from 'react-native';

const DetailScreen = ({ route, navigation }: any) => {
    const { item } = route.params;

    const openYouTube = () => {
        Linking.openURL(item.videoUrl);
    };

    const onShare = async () => {
        try {
            await Share.share({
                message: `[서울경제TV 핵심요약]\n\n${item.title}\n\n${item.summary}\n\n영상 보기: ${item.videoUrl}`,
            });
        } catch (error: any) {
            console.error(error.message);
        }
    };

    React.useLayoutEffect(() => {
        if (navigation) {
            navigation.setOptions({
                headerRight: () => (
                    <TouchableOpacity onPress={onShare} style={{ marginRight: 15 }}>
                        <Text style={{ color: '#007AFF', fontSize: 16, fontWeight: 'bold' }}>공유</Text>
                    </TouchableOpacity>
                ),
            });
        }
    }, [navigation, item]);

    return (
        <ScrollView style={styles.container}>
            <View style={styles.content}>
                <Text style={styles.date}>{item.publishedAt}</Text>
                <Text style={styles.title}>{item.title}</Text>

                <View style={styles.tagContainer}>
                    {item.keywords?.map((tag: string, index: number) => (
                        <View key={index} style={styles.tagBox}>
                            <Text style={styles.tagText}>{tag?.trim()}</Text>
                        </View>
                    ))}
                </View>

                <View style={styles.summaryBox}>
                    <Text style={styles.summaryLabel}>핵심 요약</Text>
                    {item.summaryList ? (
                        item.summaryList.map((sentence: string, index: number) => {
                            // "1. " 또는 "1. " 형태의 시작 번호 제거 (중복 방지)
                            const cleanedSentence = sentence.replace(/^\d+[\s\.]+\s*/, '');
                            return (
                                <View key={index} style={styles.summaryItem}>
                                    <Text style={styles.itemNumber}>{index + 1}.</Text>
                                    <Text style={styles.summaryText}>{cleanedSentence}</Text>
                                </View>
                            );
                        })
                    ) : (
                        <Text style={styles.summaryText}>{item.summary}</Text>
                    )}
                </View>

                <TouchableOpacity style={styles.button} onPress={openYouTube}>
                    <Text style={styles.buttonText}>유튜브에서 영상 보기</Text>
                </TouchableOpacity>

                <TouchableOpacity style={[styles.button, styles.shareButton]} onPress={onShare}>
                    <Text style={styles.buttonText}>요약 내용 공유하기</Text>
                </TouchableOpacity>
            </View>
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
    },
    content: {
        padding: 20,
        paddingBottom: 60,
    },
    date: {
        fontSize: 14,
        color: '#999',
        marginBottom: 8,
    },
    title: {
        fontSize: 22,
        fontWeight: 'bold',
        color: '#1a1a1a',
        marginBottom: 15,
    },
    tagContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        marginBottom: 20,
    },
    tagBox: {
        backgroundColor: '#E5F1FF',
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: 6,
        marginRight: 8,
        marginBottom: 8,
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: 28,
    },
    tagText: {
        fontSize: 13,
        color: '#007AFF',
        includeFontPadding: false,
        textAlignVertical: 'center',
        lineHeight: 18,
    },
    summaryBox: {
        backgroundColor: '#f9f9f9',
        padding: 20,
        borderRadius: 12,
        marginBottom: 30,
    },
    summaryLabel: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 15,
    },
    summaryItem: {
        flexDirection: 'row',
        marginBottom: 12,
    },
    itemNumber: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#007AFF',
        marginRight: 8,
        width: 25,
    },
    summaryText: {
        flex: 1,
        fontSize: 16,
        lineHeight: 24,
        color: '#444',
    },
    button: {
        backgroundColor: '#FF0000',
        padding: 15,
        borderRadius: 10,
        alignItems: 'center',
    },
    buttonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold',
    },
    shareButton: {
        backgroundColor: '#007AFF',
        marginTop: 10,
    }
});

export default DetailScreen;
