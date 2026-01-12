import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal/modal';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { useEffect, useState } from 'react';
import { Applications } from './applications';
import { NextBanner } from './banner';
import { Datasets } from './datasets';

const Home = () => {
  const { data: userInfo } = useFetchUserInfo();
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    if (userInfo?.is_admin_user) {
      setIsModalOpen(true);
    }
  }, [userInfo]);

  return (
    <section>
      <NextBanner></NextBanner>
      <section className="h-[calc(100dvh-260px)] overflow-auto px-10">
        <Datasets></Datasets>
        <Applications></Applications>
      </section>
      <Modal
        title="提示"
        open={isModalOpen}
        onOk={() => setIsModalOpen(false)}
        onCancel={() => setIsModalOpen(false)}
        footer={
          <div className="flex justify-end">
            <Button onClick={() => setIsModalOpen(false)}>确定</Button>
          </div>
        }
      >
        <div className="p-4">管理员，欢迎您！</div>
      </Modal>
    </section>
  );
};

export default Home;
