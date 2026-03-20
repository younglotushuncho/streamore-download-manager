"""
Data models for YTS Movie Monitor
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Torrent:
    """Torrent file information"""
    quality: str
    size: str
    magnet_link: str
    torrent_url: str = ''
    
    def to_dict(self):
        return {
            'quality': self.quality,
            'size': self.size,
            'magnet_link': self.magnet_link,
            'torrent_url': self.torrent_url
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            quality=data.get('quality', ''),
            size=data.get('size', ''),
            magnet_link=data.get('magnet_link', ''),
            torrent_url=data.get('torrent_url', '')
        )


@dataclass
class Movie:
    """Movie information"""
    id: str
    title: str
    year: str
    rating: float
    genres: List[str]
    description: str
    poster_url: str
    yts_url: str
    scraped_at: str
    poster_local: Optional[str] = None
    torrents: List[Torrent] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'year': self.year,
            'rating': self.rating,
            'genres': self.genres,
            'description': self.description,
            'poster_url': self.poster_url,
            'poster_local': self.poster_local,
            'yts_url': self.yts_url,
            'scraped_at': self.scraped_at,
            'torrents': [t.to_dict() for t in self.torrents]
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        torrents = [Torrent.from_dict(t) for t in data.get('torrents', [])]
        return cls(
            id=data['id'],
            title=data['title'],
            year=data.get('year', 'Unknown'),
            rating=data.get('rating', 0.0),
            genres=data.get('genres', []),
            description=data.get('description', ''),
            poster_url=data.get('poster_url', ''),
            poster_local=data.get('poster_local'),
            yts_url=data.get('yts_url', ''),
            scraped_at=data.get('scraped_at', datetime.now().isoformat()),
            torrents=torrents
        )


@dataclass
class Download:
    """Download information"""
    id: str
    movie_id: str
    movie_title: str
    quality: str
    magnet_link: str
    state: str
    progress: float
    download_rate: float
    upload_rate: float
    eta: int
    size_total: int
    size_downloaded: int
    num_peers: int
    num_seeds: int
    save_path: str
    name: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'movie_id': self.movie_id,
            'movie_title': self.movie_title,
            'quality': self.quality,
            'magnet_link': self.magnet_link,
            'state': self.state,
            'progress': self.progress,
            'download_rate': self.download_rate,
            'upload_rate': self.upload_rate,
            'eta': self.eta,
            'size_total': self.size_total,
            'size_downloaded': self.size_downloaded,
            'num_peers': self.num_peers,
            'num_seeds': self.num_seeds,
            'save_path': self.save_path,
            'name': self.name,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data['id'],
            movie_id=data['movie_id'],
            movie_title=data['movie_title'],
            quality=data['quality'],
            magnet_link=data['magnet_link'],
            state=data['state'],
            progress=data.get('progress', 0.0),
            download_rate=data.get('download_rate', 0.0),
            upload_rate=data.get('upload_rate', 0.0),
            eta=data.get('eta', 0),
            size_total=data.get('size_total', 0),
            size_downloaded=data.get('size_downloaded', 0),
            num_peers=data.get('num_peers', 0),
            num_seeds=data.get('num_seeds', 0),
            save_path=data.get('save_path', ''),
            name=data.get('name'),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            error_message=data.get('error_message')
        )
