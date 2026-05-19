import api from '@/utils/api';
import request from '@/utils/request';

class RefKbService {
  delmems(selectedkb: string, mems: string[]) {
    return request.post(api.del_mems, {
      data: { kb_id: selectedkb, mems: mems },
    });
  }

  addmems(selectedkb: string, mems: string[]) {
    return request.post(api.add_mems, {
      data: { kb_id: selectedkb, mems: mems },
    });
  }
}

export default new RefKbService();
