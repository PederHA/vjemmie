from typing import List




from ..config import YOUTUBE_VIDEO_URL


youtube = None


def youtube_search(query, *, max_results: int=50) -> List[dict]:
    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = youtube.search().list(
        q=query,
        part='id,snippet',
        maxResults=max_results
    ).execute()

    videos = []
    for search_result in search_response.get('items', []):
        if search_result['id']['kind'] == 'youtube#video':
            videos.append(search_result)

    if not videos:
        raise AttributeError("No videos found!")

    return videos


def youtube_get_top_result(query):
    results = youtube_search(query)
    return YOUTUBE_VIDEO_URL.format(id=results[0]["id"]["videoId"])
