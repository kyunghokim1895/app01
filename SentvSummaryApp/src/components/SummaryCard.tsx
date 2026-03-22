import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';

const SummaryCard = ({ item, onPress, onKeywordPress }) => {
    return (
        <TouchableOpacity style={styles.card} onPress={onPress}>
            <Text style={styles.date}>{item.publishedAt}</Text>
            <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
            <View style={styles.tagContainer}>
                {item.keywords?.map((tag, index) => (
                    <TouchableOpacity
                        key={index}
                        style={styles.tagBox}
                        onPress={() => onKeywordPress?.(tag?.trim())}
                    >
                        <Text style={styles.tagText}>{tag?.trim()}</Text>
                    </TouchableOpacity>
                ))}
            </View>
            <Text style={styles.summary} numberOfLines={3}>{item.summary}</Text>
        </TouchableOpacity>
    );
};

const styles = StyleSheet.create({
    card: {
        backgroundColor: '#fff',
        marginHorizontal: 15,
        marginVertical: 8,
        padding: 15,
        borderRadius: 12,
        elevation: 3,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
    },
    date: {
        fontSize: 12,
        color: '#999',
        marginBottom: 4,
    },
    title: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a1a',
        marginBottom: 8,
    },
    tagContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        marginBottom: 8,
    },
    tagBox: {
        backgroundColor: '#E5F1FF',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 4,
        marginRight: 6,
        marginBottom: 6,
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: 24,
    },
    tagText: {
        fontSize: 12,
        color: '#007AFF',
        includeFontPadding: false,
        textAlignVertical: 'center',
        lineHeight: 16,
    },
    summary: {
        fontSize: 14,
        color: '#444',
        lineHeight: 20,
    }
});

export default SummaryCard;
